import io
import uuid
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

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "20.0", "machine_id": "sim-machine-01"}
    headers = {"X-Dev-User": user_id}

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

    cooldown_user = f"cooldown_{uuid.uuid4().hex[:8]}"
    headers = {"X-Dev-User": cooldown_user}

    # Drop 1: initial drop succeeds
    files1 = {"image": ("bottle1.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data1 = {"weight_g": "20.0", "machine_id": "sim-machine-01"}
    resp1 = client.post("/api/drop", files=files1, data=data1, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "accepted"

    # Drop 2: immediately attempt second drop with different bytes for the SAME user
    # DUMMY_PNG_BYTES is valid PNG; adding valid bytes or dummy bytes
    files2 = {"image": ("bottle2.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data2 = {"weight_g": "20.0", "machine_id": "sim-machine-01"}
    resp2 = client.post("/api/drop", files=files2, data=data2, headers=headers)
    assert resp2.status_code == 200
    res2 = resp2.json()
    assert res2["status"] == "rejected"
    assert "Cooldown active" in res2["rejectReason"]

@patch("app.main.classify_image")
def test_get_my_drops_history(mock_classify):
    settings.ENV = "dev"
    mock_classify.return_value = ItemAnalysis(
        material="pet_bottle",
        confidence=0.92,
        contaminated=False,
        multiple_items=False,
        reason="Valid drop."
    )

    history_user = f"hist_{uuid.uuid4().hex[:8]}"
    headers = {"X-Dev-User": history_user}

    # Seed 1 drop for this user
    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "20.0", "machine_id": "sim-machine-01"}
    client.post("/api/drop", files=files, data=data, headers=headers)

    response = client.get("/api/drops?limit=10", headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert "drops" in res_data
    assert res_data["total"] >= 1
    first_drop = res_data["drops"][0]
    assert first_drop["uid"] == history_user

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

    user_id = f"bound_{uuid.uuid4().hex[:8]}"
    files = {"image": ("bottle.png", io.BytesIO(DUMMY_PNG_BYTES), "image/png")}
    data = {"weight_g": "4.0", "machine_id": "sim-machine-01"}
    headers = {"X-Dev-User": user_id}

    response = client.post("/api/drop", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "rejected"
    assert res["points"] == 0
    assert "below minimum expected weight" in res["rejectReason"]

def test_drop_endpoint_invalid_file_type():
    settings.ENV = "dev"
    user_id = f"file_{uuid.uuid4().hex[:8]}"
    files = {"image": ("doc.txt", io.BytesIO(b"hello world"), "text/plain")}
    data = {"weight_g": "20.0"}
    headers = {"X-Dev-User": user_id}

    response = client.post("/api/drop", files=files, data=data, headers=headers)
    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["detail"]
