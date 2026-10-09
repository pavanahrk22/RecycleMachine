import logging
import random
import string
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings, get_rates_config
from app.schemas import (
    DropResponse,
    UserProfile,
    DropRecord,
    DropsListResponse,
    HealthResponse,
    RedeemRequest,
    RedeemResponse,
    CampusStatsResponse
)
from app.services.classifier import classify_image, GeminiBusyException
from app.services.image_processor import compute_sha256, preprocess_image
from app.services.rules_engine import evaluate_drop
from app.services.auth import get_current_user
from app.services.firebase import (
    get_or_create_user,
    check_fraud_and_limits,
    save_drop_record,
    get_user_profile,
    get_user_drops,
    execute_redeem_transaction,
    get_campus_stats,
    get_top_leaderboard
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("campuscycle")

app = FastAPI(
    title="CampusCycle API",
    description="Backend API for CampusCycle Smart Campus Recycling System",
    version="0.3.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint for deployment monitoring (no auth required)."""
    return HealthResponse(status="ok", service="CampusCycle API")

@app.get("/api/me", response_model=UserProfile, response_model_by_alias=True, tags=["User"])
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetch profile and points balance of authenticated user."""
    profile = get_user_profile(current_user["uid"]) or current_user
    return UserProfile(
        uid=profile["uid"],
        email=profile.get("email"),
        displayName=profile.get("displayName"),
        pointsBalance=profile.get("pointsBalance", 0),
        totalGrams=profile.get("totalGrams", 0.0),
        totalItems=profile.get("totalItems", 0),
        createdAt=str(profile.get("createdAt", ""))
    )

@app.get("/api/drops", response_model=DropsListResponse, response_model_by_alias=True, tags=["Recycling"])
async def get_my_drops(
    limit: int = Query(20, ge=1, le=100, description="Max drops to return"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetch user's recent recycling history."""
    drops_raw = get_user_drops(current_user["uid"], limit=limit)
    drops = [
        DropRecord(
            id=d["id"],
            uid=d["uid"],
            machineId=d.get("machineId", "sim-machine-01"),
            material=d["material"],
            confidence=float(d.get("confidence", 0.0)),
            contaminated=bool(d.get("contaminated", False)),
            weightG=float(d.get("weightG", 0.0)),
            points=int(d.get("points", 0)),
            status=d["status"],
            rejectReason=d.get("rejectReason"),
            imageHash=d.get("imageHash", ""),
            createdAt=str(d.get("createdAt", ""))
        )
        for d in drops_raw
    ]
    return DropsListResponse(drops=drops, total=len(drops))

@app.post(
    "/api/drop",
    response_model=DropResponse,
    response_model_by_alias=True,
    tags=["Recycling"]
)
async def process_drop(
    image: UploadFile = File(..., description="Captured image of the recyclable item"),
    weight_g: float = Form(..., description="Weight of item in grams from load cell or simulator", ge=0.0),
    machine_id: str = Form("sim-machine-01", description="Identifier of the recycling machine"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    POST /api/drop endpoint:
    - Verifies user authentication.
    - Computes SHA-256 hash of raw image bytes (no images stored).
    - Runs fraud checks (12s cooldown, 24h duplicate hash, daily caps).
    - Preprocesses image (max 1024px JPEG ~85) and classifies with Gemini 3.8 Flash.
    - Evaluates points rules and weight bounds.
    - Persists drop and updates balances in ONE Firestore transaction.
    """
    uid = current_user["uid"]

    # Validate image content type
    valid_content_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    content_type = image.content_type or "image/jpeg"
    if content_type not in valid_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {content_type}. Please provide JPEG, PNG, or WebP."
        )

    # Read image bytes
    try:
        raw_img_bytes = await image.read()
        if not raw_img_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image file is empty."
            )
    except Exception as e:
        logger.error(f"Failed to read uploaded image: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded image data."
        )

    # 1. Compute SHA-256 hash (do not store raw image)
    image_hash = compute_sha256(raw_img_bytes)

    # 2. Check fraud controls (cooldown, 24h duplicate image, daily cap)
    config = get_rates_config()
    is_valid_fraud, fraud_reason = check_fraud_and_limits(
        uid=uid,
        image_hash=image_hash,
        weight_g=weight_g,
        config=config
    )

    if not is_valid_fraud:
        logger.warning(f"Drop rejected for user {uid} due to fraud check: {fraud_reason}")
        # Save rejected record in Firestore (changes no balance)
        drop_doc, balance = save_drop_record(
            uid=uid,
            machine_id=machine_id,
            material="flagged_drop",
            confidence=0.0,
            contaminated=False,
            weight_g=weight_g,
            points=0,
            is_accepted=False,
            reject_reason=fraud_reason,
            image_hash=image_hash
        )
        return DropResponse(
            status="rejected",
            material="flagged_drop",
            confidence=0.0,
            weightG=weight_g,
            points=0,
            rejectReason=fraud_reason,
            newBalance=balance,
            machineId=machine_id
        )

    # 3. Resize and compress uploaded image to max 1024px JPEG ~85
    try:
        compressed_bytes, mime = preprocess_image(raw_img_bytes, max_dim=1024, quality=85)
    except Exception as p_err:
        logger.error(f"Image preprocessing failed: {p_err}")
        compressed_bytes, mime = raw_img_bytes, content_type

    # 4. Classify with Gemini Vision (cached by image hash)
    try:
        analysis = await classify_image(
            img_bytes=compressed_bytes,
            mime_type=mime,
            image_hash=image_hash,
            timeout_seconds=30.0,
            max_retries=1
        )
        logger.info(
            f"Image classified: material={analysis.material}, "
            f"confidence={analysis.confidence:.2f}, contaminated={analysis.contaminated}"
        )
    except GeminiBusyException as g_err:
        logger.error(f"Gemini busy/timeout: {g_err}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "The AI service is busy, please try again in a few seconds",
                "retryable": True
            }
        )
    except Exception as err:
        logger.error(f"Unexpected error calling classifier: {err}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "The AI service is busy, please try again in a few seconds",
                "retryable": True
            }
        )

    # 5. Evaluate points rules and weight bounds
    is_accepted, points, reject_reason = evaluate_drop(
        analysis=analysis,
        weight_g=weight_g,
        config=config
    )

    # 6. Save drop record and update balances in ONE Firestore transaction
    drop_doc, updated_balance = save_drop_record(
        uid=uid,
        machine_id=machine_id,
        material=analysis.material,
        confidence=analysis.confidence,
        contaminated=analysis.contaminated,
        weight_g=weight_g,
        points=points,
        is_accepted=is_accepted,
        reject_reason=reject_reason,
        image_hash=image_hash
    )

    drop_status = "accepted" if is_accepted else "rejected"
    logger.info(
        f"Drop completed for user {uid}: status={drop_status}, points={points}, newBalance={updated_balance}"
    )

    return DropResponse(
        status=drop_status,
        material=analysis.material,
        confidence=analysis.confidence,
        weightG=weight_g,
        points=points,
        rejectReason=reject_reason,
        newBalance=updated_balance,
        machineId=machine_id
    )

@app.post(
    "/api/redeem",
    response_model=RedeemResponse,
    response_model_by_alias=True,
    tags=["Rewards"]
)
async def redeem_points(
    request: Optional[RedeemRequest] = Body(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    POST /api/redeem:
    - Minimum 100 points required.
    - In ONE Firestore transaction: re-reads user, verifies balance, deducts points.
    - Generates mock uppercase coupon code ('CC-XXXXXX').
    - Returns coupon code, points redeemed, and new balance.
    """
    uid = current_user["uid"]
    profile = get_user_profile(uid) or current_user
    current_balance = profile.get("pointsBalance", 0)

    if current_balance < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum 100 points required to redeem coupons. Current balance: {current_balance} pts."
        )

    # Validate or compute points to redeem (multiple of 100)
    if request and request.points is not None:
        if request.points <= 0 or request.points % 100 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Points to redeem must be a positive multiple of 100."
            )
        if request.points > current_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient points balance ({current_balance} pts) for requested {request.points} pts."
            )
        points_to_redeem = request.points
    else:
        # Default to redeeming full multiple of 100
        points_to_redeem = (current_balance // 100) * 100

    rupees = points_to_redeem // 100
    random_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    coupon_code = f"CC-{random_code}"

    try:
        new_balance, red_doc = execute_redeem_transaction(
            uid=uid,
            points_to_redeem=points_to_redeem,
            coupon_code=coupon_code,
            rupees=rupees
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        logger.error(f"Redemption transaction failed for user {uid}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process redemption transaction. Please try again."
        )

    logger.info(
        f"Redemption successful: user={uid}, redeemed={points_to_redeem} pts (Rs {rupees}), "
        f"coupon={coupon_code}, newBalance={new_balance}"
    )

    return RedeemResponse(
        couponCode=coupon_code,
        pointsRedeemed=points_to_redeem,
        newBalance=new_balance,
        rupees=rupees
    )

@app.get(
    "/api/stats",
    response_model=CampusStatsResponse,
    response_model_by_alias=True,
    tags=["Campus Stats"]
)
async def get_campus_impact_stats(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    GET /api/stats:
    - Returns campus totals (totalGrams, totalItems, countsByMaterial).
    - Returns top-5 leaderboard by totalGrams from users (first name + last initial masked, never email).
    """
    campus_stats = get_campus_stats()
    leaderboard = get_top_leaderboard(limit=5)

    return CampusStatsResponse(
        totalGrams=campus_stats.get("totalGrams", 0.0),
        totalItems=campus_stats.get("totalItems", 0),
        countsByMaterial=campus_stats.get("countsByMaterial", {}),
        leaderboard=leaderboard
    )
