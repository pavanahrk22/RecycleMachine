import io
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ItemAnalysis

client = TestClient(app)

# 1x1 transparent PNG byte data for test uploads
DUMMY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "CampusCycle API"

@patch("app.main.classify_image")
def test_drop_endpoint_accepted(mock_classify):
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.94,
        contaminated=False,
        multiple_items=False,
        reason="Clean 20g PET bottle."
    )

    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "20.0", "machine_id": "sim-machine-01"}

    response = client.post("/api/drop", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "accepted"
    assert res["material"] == "pet_bottle"
    assert res["confidence"] == 0.94
    assert res["weightG"] == 20.0
    assert res["points"] == 20
    assert res["rejectReason"] is None

@patch("app.main.classify_image")
def test_drop_endpoint_rejected_out_of_bounds(mock_classify):
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.90,
        contaminated=False,
        multiple_items=False,
        reason="Valid bottle image."
    )

    # 4g is below the 8g minimum for pet_bottle
    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "4.0", "machine_id": "sim-machine-01"}

    response = client.post("/api/drop", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "rejected"
    assert res["points"] == 0
    assert "below minimum expected weight" in res["rejectReason"]

@patch("app.main.classify_image")
def test_drop_endpoint_rejected_contaminated(mock_classify):
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.88,
        contaminated=True,
        multiple_items=False,
        reason="Bottle contains liquid."
    )

    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "20.0", "machine_id": "sim-machine-01"}

    response = client.post("/api/drop", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "rejected"
    assert res["points"] == 0
    assert "Bottle contains liquid." in res["rejectReason"]

def test_drop_endpoint_invalid_file_type():
    files = {"image": ("doc.txt", io.BytesIO(b"hello world"), "text/plain")}
    data = {"weight_g": "20.0"}

    response = client.post("/api/drop", files=files, data=data)
    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["detail"]
