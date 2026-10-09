import io
from PIL import Image
from app.services.image_processor import compute_sha256, preprocess_image

def test_compute_sha256():
    data = b"campuscycle_sample_data"
    hash_val = compute_sha256(data)
    assert len(hash_val) == 64
    assert hash_val == compute_sha256(data)

def test_preprocess_image_resizing_and_compression():
    # Create large 2000x1500 RGB image
    large_img = Image.new("RGB", (2000, 1500), color="blue")
    buffer = io.BytesIO()
    large_img.save(buffer, format="PNG")
    raw_bytes = buffer.getvalue()

    compressed_bytes, mime = preprocess_image(raw_bytes, max_dim=1024, quality=85)
    assert mime == "image/jpeg"
    assert len(compressed_bytes) > 0

    # Verify compressed dimensions are <= 1024
    result_img = Image.open(io.BytesIO(compressed_bytes))
    w, h = result_img.size
    assert max(w, h) <= 1024
    assert result_img.format == "JPEG"
