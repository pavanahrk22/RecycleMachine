import asyncio
import logging
import time
from typing import Optional
from google import genai
from google.genai import types
from app.config import settings
from app.schemas import ItemAnalysis

logger = logging.getLogger(__name__)

VISION_PROMPT = (
    "You are the vision classifier for a campus recycling machine. "
    "Look at the item in the image and return JSON only. "
    "Fields: material (one of pet_bottle, aluminium_can, rigid_plastic, snack_wrapper, non_recyclable, no_item), "
    "confidence (0 to 1), contaminated (true if visibly dirty, wet, or containing liquid, food, or foreign objects), "
    "multiple_items (true if more than one item is visible), reason (one short sentence). "
    "If no clear single item is visible, use no_item. Do not guess: if unsure, lower the confidence."
)

_client: Optional[genai.Client] = None

def get_genai_client() -> genai.Client:
    """Lazily initialize and return the Google GenAI client."""
    global _client
    if _client is None:
        if settings.GEMINI_API_KEY:
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            _client = genai.Client()
    return _client

def _classify_sync(img_bytes: bytes, mime_type: str = "image/jpeg", model_name: str = None) -> ItemAnalysis:
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
        # Fallback if raw text JSON was returned without pydantic auto-population
        return ItemAnalysis.model_validate_json(response.text)
    else:
        raise ValueError("Empty or invalid response received from Gemini model.")

async def classify_image(
    img_bytes: bytes,
    mime_type: str = "image/jpeg",
    timeout_seconds: float = 10.0,
    max_retries: int = 1
) -> ItemAnalysis:
    """Classifies an image with timeout and 1 retry.
    
    If MOCK_CLASSIFICATION is enabled (e.g. offline testing), returns a mock result.
    """
    if settings.MOCK_CLASSIFICATION:
        logger.info("Using mock classification mode.")
        return ItemAnalysis(
            material="pet_bottle",
            confidence=0.95,
            contaminated=False,
            multiple_items=False,
            reason="Mock PET bottle identified successfully."
        )

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Classifying image with Gemini (attempt {attempt + 1}/{max_retries + 1})...")
            result = await asyncio.wait_for(
                asyncio.to_thread(_classify_sync, img_bytes, mime_type),
                timeout=timeout_seconds
            )
            return result
        except asyncio.TimeoutError as te:
            last_error = te
            logger.warning(f"Gemini classification timed out on attempt {attempt + 1}")
        except Exception as exc:
            last_error = exc
            logger.warning(f"Gemini classification failed on attempt {attempt + 1}: {exc}")

        if attempt < max_retries:
            await asyncio.sleep(0.5)

    raise RuntimeError(
        f"Unable to analyze item image. AI service timed out or encountered an error ({str(last_error)}). Please try again."
    )
