import logging
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Depends
from app.config import settings
from app.services.firebase import verify_firebase_token, get_or_create_user

logger = logging.getLogger("campuscycle.auth")

async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_dev_user: Optional[str] = Header(None, alias="X-Dev-User")
) -> Dict[str, Any]:
    """
    Authenticates requests for protected endpoints.
    - Production: Strictly verifies Firebase ID token from 'Authorization: Bearer <token>' header.
    - Development (ENV=dev): Allows 'X-Dev-User' header for fast prototyping and automated tests.
    - Ensures user document exists in users/{uid} on first request.
    """
    # 1. Check Dev-Only Auth Bypass
    if settings.is_dev and x_dev_user:
        dev_uid = x_dev_user.strip()
        if not dev_uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-Dev-User header cannot be empty."
            )
        dev_email = f"{dev_uid}@campus.edu"
        user_record = get_or_create_user(
            uid=dev_uid,
            email=dev_email,
            display_name=dev_uid
        )
        return user_record

    # 2. In Production (or Dev without X-Dev-User), require Bearer token
    if not authorization or not authorization.startswith("Bearer "):
        if settings.is_dev:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication. Provide 'Authorization: Bearer <token>' or 'X-Dev-User: <uid>' in dev mode."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <Firebase ID token>'."
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token cannot be empty."
        )

    try:
        decoded_user = verify_firebase_token(token)
    except Exception as exc:
        logger.warning(f"Invalid Firebase ID token: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token."
        )

    # 3. Ensure user document in Firestore on first request
    user_record = get_or_create_user(
        uid=decoded_user["uid"],
        email=decoded_user.get("email"),
        display_name=decoded_user.get("displayName")
    )
    return user_record
