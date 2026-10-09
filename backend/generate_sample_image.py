"""Helper script to create a sample test image for curl commands."""
from pathlib import Path

# 1x1 transparent PNG bytes
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

output_path = Path(__file__).parent / "sample_item.png"
with open(output_path, "wb") as f:
    f.write(PNG_BYTES)
print(f"Created sample image: {output_path}")
