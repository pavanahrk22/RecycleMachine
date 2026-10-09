import asyncio
import logging
import traceback
from typing import Optional, Dict
from google import genai
from google.genai import types
from app.config import settings
from app.schemas import ItemAnalysis

logger = logging.getLogger("campuscycle.classifier")

VISION_PROMPT = (
    "You are the vision classifier for a campus recycling machine. "
    "Look at the item in the image and return JSON only. "
    "Fields: material (one of pet_bottle, aluminium_can, rigid_plastic, snack_wrapper, non_recyclable, no_item), "
    "confidence (0 to 1), contaminated (true if visibly dirty, wet, or containing liquid, food, or foreign objects), "
    "multiple_items (true if more than one item is visible), reason (one short sentence). "
    "If no clear single item is visible, use no_item. Do not guess: if unsure, lower the confidence."
)

class GeminiBusyException(Exception):
    """Raised when Gemini API encounters timeouts or transient errors."""
    def __init__(self, message: str = "The AI service is busy, please try again in a few seconds"):
        super().__init__(message)
        self.message = message
        self.retryable = True

_client: Optional[genai.Client] = None

# In-memory cache keyed by SHA-256 hash of image to conserve quota
_classification_cache: Dict[str, ItemAnalysis] = {}

def get_genai_client() -> genai.Client:
    """Lazily initialize and return the Google GenAI client."""
    global _client
    if _client is None:
        if settings.GEMINI_API_KEY:
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            _client = genai.Client()
    return _client

def _classify_sync(img_bytes: bytes, mime_type: str = "image/jpeg", model_name: str = "gemini-3.8-flash") -> ItemAnalysis:
    """Internal synchronous call to Gemini vision model with structured output."""
    client = get_genai_client()
    model = model_name or settings.GEMINI_MODEL

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
            VISION_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ItemAnalysis,
            temperature=0.1
        )
    )

    if response.parsed and isinstance(response.parsed, ItemAnalysis):
        return response.parsed
    elif response.parsed and isinstance(response.parsed, dict):
        return ItemAnalysis(**response.parsed)
    elif response.text:
        return ItemAnalysis.model_validate_json(response.text)
    else:
        raise ValueError("Empty or invalid structured response received from Gemini model.")

async def classify_image(
    img_bytes: bytes,
    mime_type: str = "image/jpeg",
    image_hash: Optional[str] = None,
    timeout_seconds: float = 30.0,
    max_retries: int = 1
) -> ItemAnalysis:
    """Classifies an image using Gemini 3.8 Flash with cache lookup, 30s timeout, and retry on 429/5xx/timeout.
    
    If MOCK_CLASSIFICATION is enabled, returns a deterministic mock result.
    """
    # 1. Check classification cache
    if image_hash and image_hash in _classification_cache:
        logger.info(f"Cache hit for image hash: {image_hash[:12]}...")
        return _classification_cache[image_hash]

    if settings.MOCK_CLASSIFICATION:
        logger.info("Using mock classification mode.")
        result = ItemAnalysis(
            material="pet_bottle",
            confidence=0.95,
            contaminated=False,
            multiple_items=False,
            reason="Mock PET bottle identified successfully."
        )
        if image_hash:
            _classification_cache[image_hash] = result
        return result

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Calling Gemini model '{settings.GEMINI_MODEL}' (attempt {attempt + 1}/{max_retries + 1}, timeout={timeout_seconds}s)..."
            )
            result = await asyncio.wait_for(
                asyncio.to_thread(_classify_sync, img_bytes, mime_type, settings.GEMINI_MODEL),
                timeout=timeout_seconds
            )
            
            # Cache successful result
            if image_hash:
                _classification_cache[image_hash] = result

            return result

        except Exception as exc:
            last_error = exc
            # Log the real Gemini exception type and message to the console
            exc_type_name = type(exc).__name__
            exc_msg = str(exc)
            logger.error(
                f"[Gemini Exception on attempt {attempt + 1}] Type: {exc_type_name} | Message: {exc_msg}"
            )

            # Check if retryable: timeout, 429 (rate limit), or 5xx (server error)
            is_timeout = isinstance(exc, asyncio.TimeoutError)
            err_lower = exc_msg.lower()
            is_429 = "429" in err_lower or "resource_exhausted" in err_lower or "quota" in err_lower
            is_5xx = any(code in err_lower for code in ["500", "502", "503", "504", "internal", "unavailable"])
            is_retryable = is_timeout or is_429 or is_5xx

            if attempt < max_retries and is_retryable:
                retry_delay = 2.5
                logger.warning(
                    f"Transient Gemini error detected ({exc_type_name}). Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
            else:
                break

    raise GeminiBusyException("The AI service is busy, please try again in a few seconds")
