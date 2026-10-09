import os
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import firebase_admin
from firebase_admin import credentials, firestore, auth

from app.config import settings

logger = logging.getLogger("campuscycle.firebase")

_db = None
_is_mock_db = False

def mask_user_name(display_name: Optional[str], email: Optional[str]) -> str:
    """Format name as first name plus last initial, never exposing email."""
    name = (display_name or "").strip()
    if not name or "@" in name:
        if email and "@" in email:
            name = email.split("@")[0]
        else:
            return "Student"

    tokens = [t for t in re.split(r"[\s_.]+", name) if t]
    if not tokens:
        return "Student"

    first = tokens[0].capitalize()
    if len(tokens) >= 2 and tokens[1]:
        last_initial = tokens[1][0].upper()
        return f"{first} {last_initial}."
    return first

class InMemoryFirestore:
    """Fast, thread-safe in-memory mock Firestore for dev/testing when serviceAccountKey is absent."""
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.drops: Dict[str, Dict[str, Any]] = {}
        self.redemptions: Dict[str, Dict[str, Any]] = {}
        self.stats: Dict[str, Dict[str, Any]] = {
            "campus": {
                "totalGrams": 0.0,
                "totalItems": 0,
                "countsByMaterial": {}
            }
        }

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        return self.users.get(uid)

    def set_user(self, uid: str, data: Dict[str, Any]):
        self.users[uid] = data

    def get_drops_for_user(self, uid: str, limit: int = 20) -> List[Dict[str, Any]]:
        user_drops = [d for d in self.drops.values() if d.get("uid") == uid]
        user_drops.sort(key=lambda d: str(d.get("createdAt", "")), reverse=True)
        return user_drops[:limit]

    def execute_drop_transaction(
        self,
        uid: str,
        drop_data: Dict[str, Any],
        is_accepted: bool,
        points: int,
        weight_g: float,
        material: str
    ) -> int:
        drop_id = drop_data["id"]
        self.drops[drop_id] = drop_data

        user = self.users.get(uid, {
            "uid": uid,
            "displayName": uid,
            "email": "",
            "pointsBalance": 0,
            "totalGrams": 0.0,
            "totalItems": 0,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })

        if is_accepted:
            user["pointsBalance"] = user.get("pointsBalance", 0) + points
            user["totalGrams"] = round(user.get("totalGrams", 0.0) + weight_g, 2)
            user["totalItems"] = user.get("totalItems", 0) + 1
            self.users[uid] = user

            campus_stats = self.stats["campus"]
            campus_stats["totalGrams"] = round(campus_stats.get("totalGrams", 0.0) + weight_g, 2)
            campus_stats["totalItems"] = campus_stats.get("totalItems", 0) + 1
            counts = campus_stats.setdefault("countsByMaterial", {})
            counts[material] = counts.get(material, 0) + 1

        return user.get("pointsBalance", 0)

    def execute_redeem_transaction(
        self,
        uid: str,
        points_to_redeem: int,
        coupon_code: str,
        rupees: int
    ) -> Tuple[int, Dict[str, Any]]:
        user = self.users.get(uid)
        current_balance = user.get("pointsBalance", 0) if user else 0
        if current_balance < points_to_redeem:
            raise ValueError(f"Insufficient balance ({current_balance} pts) to redeem {points_to_redeem} pts.")

        user["pointsBalance"] = current_balance - points_to_redeem
        self.users[uid] = user

        red_id = f"red_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        red_doc = {
            "id": red_id,
            "uid": uid,
            "points": points_to_redeem,
            "rupees": rupees,
            "couponCode": coupon_code,
            "createdAt": now_iso
        }
        self.redemptions[red_id] = red_doc
        return user["pointsBalance"], red_doc

def init_firebase():
    """Initializes Firebase Admin SDK with service account or falls back to in-memory store in dev."""
    global _db, _is_mock_db
    if _db is not None:
        return _db

    cred_path_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or settings.GOOGLE_APPLICATION_CREDENTIALS
    candidate_paths = [
        cred_path_env,
        "serviceAccountKey.json",
        "backend/serviceAccountKey.json",
        str(Path(__file__).resolve().parent.parent.parent / "serviceAccountKey.json")
    ]

    found_path = None
    for p in candidate_paths:
        if p and Path(p).exists():
            found_path = str(Path(p).resolve())
            break

    if found_path:
        try:
            logger.info(f"Initializing Firebase Admin with service account key: {found_path}")
            if not firebase_admin._apps:
                cred = credentials.Certificate(found_path)
                firebase_admin.initialize_app(cred)
            _db = firestore.client()
            _is_mock_db = False
            logger.info("Firestore client initialized successfully.")
            return _db
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin with key {found_path}: {e}")

    logger.warning("No valid Firebase service account found. Using in-memory Firestore engine for dev/test.")
    if not settings.is_dev: raise RuntimeError('Firebase service account missing or failed to load')
    _db = InMemoryFirestore()
    _is_mock_db = True
    return _db

def get_db():
    global _db
    if _db is None:
        return init_firebase()
    return _db

def verify_firebase_token(token: str) -> Dict[str, Any]:
    """Verify Firebase ID token. In mock mode or dev, handles token parsing."""
    try:
        init_firebase()
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "displayName": decoded.get("name") or decoded.get("displayName")
        }
    except Exception as exc:
        logger.error(f"Firebase token verification failed: {exc}")
        raise

def get_or_create_user(uid: str, email: Optional[str] = None, display_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch existing user document or create a new user profile on first request."""
    db = get_db()
    now_iso = datetime.now(timezone.utc).isoformat()

    if _is_mock_db:
        user = db.get_user(uid)
        if not user:
            user = {
                "uid": uid,
                "displayName": display_name or (email.split("@")[0] if email else uid),
                "email": email or "",
                "pointsBalance": 0,
                "totalGrams": 0.0,
                "totalItems": 0,
                "createdAt": now_iso
            }
            db.set_user(uid, user)
        return user

    # Real Firestore
    user_ref = db.collection("users").document(uid)
    snap = user_ref.get()
    if snap.exists:
        data = snap.to_dict()
        data["uid"] = uid
        return data

    new_user = {
        "displayName": display_name or (email.split("@")[0] if email else uid),
        "email": email or "",
        "pointsBalance": 0,
        "totalGrams": 0.0,
        "totalItems": 0,
        "createdAt": firestore.SERVER_TIMESTAMP
    }
    user_ref.set(new_user)
    new_user["uid"] = uid
    new_user["createdAt"] = now_iso
    return new_user

def check_fraud_and_limits(
    uid: str,
    image_hash: str,
    weight_g: float,
    config: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Fraud and abuse checks:
    - Cooldown between drops (default 12 seconds)
    - Duplicate image hash check within 24 hours
    - Daily drop count and weight limits (30 drops or 1000g)
    """
    db = get_db()
    cooldown_seconds = config.get("cooldown_seconds", 12)
    daily_caps = config.get("daily_caps", {})
    max_drops = daily_caps.get("max_drops", 30)
    max_grams = daily_caps.get("max_grams", 1000.0)

    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()

    drops = []
    if _is_mock_db:
        drops = [d for d in db.drops.values() if d.get("uid") == uid]
    else:
        # Query drops for user
        docs = db.collection("drops").where("uid", "==", uid).stream()
        for doc in docs:
            drops.append(doc.to_dict())

    if drops:
        # 1. Cooldown check: Check most recent drop
        drops_sorted = sorted(drops, key=lambda d: str(d.get("createdAt", "")), reverse=True)
        latest_drop = drops_sorted[0]
        latest_time_str = latest_drop.get("createdAt")
        if latest_time_str:
            try:
                latest_time = datetime.fromisoformat(str(latest_time_str).replace("Z", "+00:00"))
                elapsed = (now - latest_time).total_seconds()
                if elapsed < cooldown_seconds:
                    wait_sec = int(cooldown_seconds - elapsed) + 1
                    return False, f"Cooldown active. Please wait {wait_sec}s before dropping another item."
            except Exception as e:
                logger.warning(f"Could not parse drop timestamp for cooldown: {e}")

        # 2. Duplicate image hash check within 24 hours
        for d in drops:
            if d.get("imageHash") == image_hash:
                d_time_str = str(d.get("createdAt", ""))
                if d_time_str >= twenty_four_hours_ago:
                    return False, "Duplicate image detected. You cannot resubmit the same photo within 24 hours."

        # 3. Daily caps: sum accepted drops in last 24h
        recent_accepted = [
            d for d in drops
            if d.get("status") == "accepted" and str(d.get("createdAt", "")) >= twenty_four_hours_ago
        ]
        if len(recent_accepted) >= max_drops:
            return False, f"Daily limit of {max_drops} drops reached. Please return tomorrow."

        daily_grams_sum = sum(float(d.get("weightG", 0.0)) for d in recent_accepted)
        if (daily_grams_sum + weight_g) > max_grams:
            return False, f"Daily limit of {max_grams:.0f}g reached (currently at {daily_grams_sum:.1f}g). Please return tomorrow."

    return True, None

def save_drop_record(
    uid: str,
    machine_id: str,
    material: str,
    confidence: float,
    contaminated: bool,
    weight_g: float,
    points: int,
    is_accepted: bool,
    reject_reason: Optional[str],
    image_hash: str
) -> Tuple[Dict[str, Any], int]:
    """Write drop record, update user balance, and update campus stats in ONE Firestore transaction."""
    db = get_db()
    drop_id = f"drop_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    drop_data = {
        "id": drop_id,
        "uid": uid,
        "machineId": machine_id,
        "material": material,
        "confidence": confidence,
        "contaminated": contaminated,
        "weightG": weight_g,
        "points": points if is_accepted else 0,
        "status": "accepted" if is_accepted else "rejected",
        "rejectReason": reject_reason,
        "imageHash": image_hash,
        "createdAt": now_iso
    }

    if _is_mock_db:
        new_balance = db.execute_drop_transaction(
            uid=uid,
            drop_data=drop_data,
            is_accepted=is_accepted,
            points=points,
            weight_g=weight_g,
            material=material
        )
        return drop_data, new_balance

    # Real Firestore Transaction
    transaction = db.transaction()
    drop_ref = db.collection("drops").document(drop_id)
    user_ref = db.collection("users").document(uid)
    stats_ref = db.collection("stats").document("campus")

    @firestore.transactional
    def _run_in_transaction(txn):
        user_snap = user_ref.get(transaction=txn)
        current_balance = 0
        if user_snap.exists:
            current_balance = user_snap.to_dict().get("pointsBalance", 0)

        # 1. Write drop document
        txn.set(drop_ref, drop_data)

        # 2. If accepted, update user balance and stats
        if is_accepted:
            txn.update(user_ref, {
                "pointsBalance": firestore.Increment(points),
                "totalGrams": firestore.Increment(weight_g),
                "totalItems": firestore.Increment(1)
            })
            txn.set(stats_ref, {
                "totalGrams": firestore.Increment(weight_g),
                "totalItems": firestore.Increment(1),
                f"countsByMaterial.{material}": firestore.Increment(1)
            }, merge=True)
            return current_balance + points
        
        return current_balance

    new_balance = _run_in_transaction(transaction)
    return drop_data, new_balance

def execute_redeem_transaction(
    uid: str,
    points_to_redeem: int,
    coupon_code: str,
    rupees: int
) -> Tuple[int, Dict[str, Any]]:
    """In ONE Firestore transaction: re-read users/{uid}, verify balance >= 100, deduct points, create redemptions/{id}."""
    db = get_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    red_id = f"red_{uuid.uuid4().hex[:12]}"
    red_doc = {
        "id": red_id,
        "uid": uid,
        "points": points_to_redeem,
        "rupees": rupees,
        "couponCode": coupon_code,
        "createdAt": now_iso
    }

    if _is_mock_db:
        return db.execute_redeem_transaction(uid, points_to_redeem, coupon_code, rupees)

    transaction = db.transaction()
    user_ref = db.collection("users").document(uid)
    red_ref = db.collection("redemptions").document(red_id)

    @firestore.transactional
    def _run_redeem(txn):
        user_snap = user_ref.get(transaction=txn)
        if not user_snap.exists:
            raise ValueError("User profile not found.")
        user_data = user_snap.to_dict()
        current_balance = user_data.get("pointsBalance", 0)
        if current_balance < points_to_redeem:
            raise ValueError(f"Insufficient balance ({current_balance} pts) to redeem {points_to_redeem} pts.")

        new_balance = current_balance - points_to_redeem
        txn.update(user_ref, {"pointsBalance": new_balance})
        txn.set(red_ref, red_doc)
        return new_balance

    new_balance = _run_redeem(transaction)
    return new_balance, red_doc

def get_user_profile(uid: str) -> Optional[Dict[str, Any]]:
    """Return user profile and balance."""
    db = get_db()
    if _is_mock_db:
        return db.get_user(uid)

    snap = db.collection("users").document(uid).get()
    if snap.exists:
        data = snap.to_dict()
        data["uid"] = uid
        return data
    return None

def get_user_drops(uid: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent drops for user ordered by createdAt desc."""
    db = get_db()
    if _is_mock_db:
        return db.get_drops_for_user(uid, limit=limit)

    # Query by uid without server-side ordering to eliminate composite index requirement
    docs = db.collection("drops").where("uid", "==", uid).stream()
    drops = [d.to_dict() for d in docs]
    drops.sort(key=lambda d: str(d.get("createdAt", "")), reverse=True)
    return drops[:limit]

def get_campus_stats() -> Dict[str, Any]:
    """Return campus aggregates from stats/campus (zeros if missing)."""
    db = get_db()
    if _is_mock_db:
        campus = db.stats.get("campus", {})
        return {
            "totalGrams": float(campus.get("totalGrams", 0.0)),
            "totalItems": int(campus.get("totalItems", 0)),
            "countsByMaterial": dict(campus.get("countsByMaterial", {}))
        }

    snap = db.collection("stats").document("campus").get()
    if snap.exists:
        data = snap.to_dict()
        return {
            "totalGrams": float(data.get("totalGrams", 0.0)),
            "totalItems": int(data.get("totalItems", 0)),
            "countsByMaterial": dict(data.get("countsByMaterial", {}))
        }
    return {
        "totalGrams": 0.0,
        "totalItems": 0,
        "countsByMaterial": {}
    }

def get_top_leaderboard(limit: int = 5) -> List[Dict[str, Any]]:
    """Return top-N leaderboard by totalGrams from users with masked names."""
    db = get_db()
    users_list = []
    if _is_mock_db:
        users_list = list(db.users.values())
    else:
        docs = db.collection("users").stream()
        for doc in docs:
            users_list.append(doc.to_dict())

    # Sort by totalGrams descending
    users_list.sort(key=lambda u: float(u.get("totalGrams", 0.0)), reverse=True)
    top_users = users_list[:limit]

    leaderboard = []
    for rank, u in enumerate(top_users, start=1):
        leaderboard.append({
            "rank": rank,
            "displayName": mask_user_name(u.get("displayName"), u.get("email")),
            "totalGrams": float(u.get("totalGrams", 0.0)),
            "totalItems": int(u.get("totalItems", 0))
        })
    return leaderboard
