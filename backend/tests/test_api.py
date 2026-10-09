import io
import time
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ItemAnalysis
from app.config import settings

client = TestClient(app)

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
def test_drop_endpoint_accepted_with_balance_update(mock_classify):
    settings.ENV = "dev"
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.94,
        contaminated=False,
        multiple_items=False,
        reason="Clean 20g PET bottle."
    )

    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "20.0", "machine_id": "sim-machine-01"}
    headers = {"X-Dev-User": "user_m2_test"}

    response = client.post("/api/drop", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "accepted"
    assert res["material"] == "pet_bottle"
    assert res["confidence"] == 0.94
    assert res["weightG"] == 20.0
    assert res["points"] == 20
    assert res["newBalance"] == 20
    assert res["rejectReason"] is None

@patch("app.main.classify_image")
def test_drop_endpoint_cooldown_trigger(mock_classify):
    settings.ENV = "dev"
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.90,
        contaminated=False,
        multiple_items=False,
        reason="Bottle image."
    )

    # Immediately attempt second drop with different bytes for same user
    different_bytes = DUMMY_PNG_BYTES + b"salt"
    files = {"image": ("bottle2.png", io.BytesIO(different_bytes), "image/png")}
    data = {"weight_g": "20.0", "machine_id": "sim-machine-01"}
    headers = {"X-Dev-User": "user_m2_test"}

    response = client.post("/api/drop", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "rejected"
    assert "Cooldown active" in res["rejectReason"]

def test_get_my_drops_history():
    settings.ENV = "dev"
    headers = {"X-Dev-User": "user_m2_test"}
    response = client.get("/api/drops?limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "drops" in data
    assert data["total"] >= 1
    first_drop = data["drops"][0]
    assert "id" in first_drop
    assert first_drop["uid"] == "user_m2_test"
    assert "imageHash" in first_drop

@patch("app.main.classify_image")
def test_drop_endpoint_rejected_out_of_bounds(mock_classify):
    settings.ENV = "dev"
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.90,
        contaminated=False,
        multiple_items=False,
        reason="Valid bottle image."
    )

    # 4g is below the 8g minimum for pet_bottle
    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES + b"unique_weight"), "image/png")}
    data = {"weight_g": "4.0", "machine_id": "sim-machine-01"}
    headers = {"X-Dev-User": "weight_bound_user"}

    response = client.post("/api/drop", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "rejected"
    assert res["points"] == 0
    assert "below minimum expected weight" in res["rejectReason"]
    assert res["newBalance"] == 0

def test_drop_endpoint_invalid_file_type():
    settings.ENV = "dev"
    files = {"image": ("doc.txt", io.BytesIO(b"hello world"), "text/plain")}
    data = {"weight_g": "20.0"}
    headers = {"X-Dev-User": "file_type_user"}

    response = client.post("/api/drop", files=files, data=data, headers=headers)
    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["detail"]
