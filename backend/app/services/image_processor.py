import io
import hashlib
from typing import Tuple
from PIL import Image

def compute_sha256(data: bytes) -> str:
    """Compute hex SHA-256 hash of byte data."""
    return hashlib.sha256(data).hexdigest()

def preprocess_image(img_bytes: bytes, max_dim: int = 1024, quality: int = 85) -> Tuple[bytes, str]:
    """Resize image to maximum 1024px dimension and compress to JPEG (~85 quality).
    
    Returns:
        (compressed_bytes, mime_type)
    """
    image = Image.open(io.BytesIO(img_bytes))

    # Convert modes (RGBA, P, palette) to RGB for JPEG compatibility
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize if either dimension exceeds max_dim while preserving aspect ratio
    width, height = image.size
    if width > max_dim or height > max_dim:
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    output_buffer = io.BytesIO()
    image.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    compressed_bytes = output_buffer.getvalue()

    return compressed_bytes, "image/jpeg"
