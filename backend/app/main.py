import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings, get_rates_config
from app.schemas import DropResponse, HealthResponse
from app.services.classifier import classify_image
from app.services.rules_engine import evaluate_drop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("campuscycle")

app = FastAPI(
    title="CampusCycle API",
    description="Backend API for CampusCycle Smart Campus Recycling System",
    version="0.1.0"
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
    """Health check endpoint for deployment monitoring."""
    return HealthResponse(status="ok", service="CampusCycle API")

@app.post(
    "/api/drop",
    response_model=DropResponse,
    response_model_by_alias=True,
    tags=["Recycling"]
)
async def process_drop(
    image: UploadFile = File(..., description="Captured image of the recyclable item"),
    weight_g: float = Form(..., description="Weight of item in grams from load cell or simulator", ge=0.0),
    machine_id: str = Form("sim-machine-01", description="Identifier of the recycling machine")
):
    """
    Simulated machine drop endpoint (Milestone 1).
    - Accepts image and weight reading.
    - Classifies material and contamination using Gemini Vision API.
    - Validates weight bounds and calculates points based on configured rates.
    - Returns structured classification, validation status, and earned points.
    """
    # Validate MIME type
    valid_content_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    content_type = image.content_type or "image/jpeg"
    if content_type not in valid_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {content_type}. Please provide JPEG, PNG, or WebP."
        )

    # Read image bytes
    try:
        img_bytes = await image.read()
        if not img_bytes:
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

    # Classify item with Gemini Vision
    try:
        analysis = await classify_image(img_bytes=img_bytes, mime_type=content_type)
        logger.info(
            f"Image classified: material={analysis.material}, "
            f"confidence={analysis.confidence:.2f}, contaminated={analysis.contaminated}"
        )
    except RuntimeError as r_err:
        logger.error(f"Gemini classification error: {r_err}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": str(r_err),
                "retryable": True
            }
        )
    except Exception as err:
        logger.error(f"Unexpected classification failure: {err}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Failed to analyze image due to an internal error. Please try again.",
                "retryable": True
            }
        )

    # Evaluate rules: fraud checks, bounds, and points calculation
    config = get_rates_config()
    is_accepted, points, reject_reason = evaluate_drop(
        analysis=analysis,
        weight_g=weight_g,
        config=config
    )

    drop_status = "accepted" if is_accepted else "rejected"

    logger.info(
        f"Drop result: status={drop_status}, points={points}, "
        f"material={analysis.material}, weight={weight_g}g, reason={reject_reason}"
    )

    return DropResponse(
        status=drop_status,
        material=analysis.material,
        confidence=analysis.confidence,
        weightG=weight_g,
        points=points,
        rejectReason=reject_reason,
        newBalance=None,  # Populated in Milestone 2 with Firestore user balance
        machineId=machine_id
    )
