import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.firebase import get_or_create_user, save_drop_record, InMemoryFirestore, mask_user_name

client = TestClient(app)

@pytest.fixture(autouse=True)
def enable_dev_mode():
    original_env = settings.ENV
    settings.ENV = "dev"
    yield
    settings.ENV = original_env

def test_mask_user_name_privacy():
    assert mask_user_name("Pavana Hegde", "pavana@campus.edu") == "Pavana H."
    assert mask_user_name("Alice", "alice@campus.edu") == "Alice"
    assert mask_user_name("student_pavana", "student_pavana@campus.edu") == "Student P."
    # Never expose email
    assert "@" not in mask_user_name(None, "secret_email@campus.edu")
    assert mask_user_name("secret_email@campus.edu", "secret_email@campus.edu") == "Secret E."

def test_redeem_fails_below_100_points():
    unique_uid = f"user_{uuid.uuid4().hex[:8]}"
    get_or_create_user(unique_uid, f"{unique_uid}@campus.edu", "Test User")

    # User starts with 0 points
    response = client.post(
        "/api/redeem",
        headers={"X-Dev-User": unique_uid},
        json={"points": 100}
    )
    assert response.status_code == 400
    assert "Minimum 100 points required" in response.json()["detail"]

def test_redeem_successful_full_and_partial():
    unique_uid = f"user_{uuid.uuid4().hex[:8]}"
    user = get_or_create_user(unique_uid, f"{unique_uid}@campus.edu", "John Doe")

    # Give user 250 points
    from app.services.firebase import get_db, _is_mock_db
    db = get_db()
    if _is_mock_db:
        db.users[unique_uid]["pointsBalance"] = 250
        db.users[unique_uid]["totalGrams"] = 250.0
        db.users[unique_uid]["totalItems"] = 5
    else:
        db.collection("users").document(unique_uid).update({
            "pointsBalance": 250,
            "totalGrams": 250.0,
            "totalItems": 5
        })

    # 1. Redeem 100 points specifically
    resp1 = client.post(
        "/api/redeem",
        headers={"X-Dev-User": unique_uid},
        json={"points": 100}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["couponCode"].startswith("CC-")
    assert len(data1["couponCode"]) == 9 # CC-XXXXXX
    assert data1["pointsRedeemed"] == 100
    assert data1["rupees"] == 1
    assert data1["newBalance"] == 150

    # 2. Redeem remaining full multiple of 100 (without specifying body)
    resp2 = client.post(
        "/api/redeem",
        headers={"X-Dev-User": unique_uid}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["couponCode"].startswith("CC-")
    assert data2["pointsRedeemed"] == 100
    assert data2["rupees"] == 1
    assert data2["newBalance"] == 50 # 50 leftover points cannot be redeemed

    # 3. Attempting another redeem with 50 points remaining fails
    resp3 = client.post(
        "/api/redeem",
        headers={"X-Dev-User": unique_uid}
    )
    assert resp3.status_code == 400
    assert "Minimum 100 points required" in resp3.json()["detail"]

def test_redeem_invalid_multiple():
    unique_uid = f"user_{uuid.uuid4().hex[:8]}"
    get_or_create_user(unique_uid, f"{unique_uid}@campus.edu", "Jane Smith")

    from app.services.firebase import get_db, _is_mock_db
    db = get_db()
    if _is_mock_db:
        db.users[unique_uid]["pointsBalance"] = 300
    else:
        db.collection("users").document(unique_uid).update({"pointsBalance": 300})

    # Cannot redeem 150 (not multiple of 100)
    resp = client.post(
        "/api/redeem",
        headers={"X-Dev-User": unique_uid},
        json={"points": 150}
    )
    assert resp.status_code == 400
    assert "positive multiple of 100" in resp.json()["detail"]

def test_campus_stats_and_leaderboard():
    unique_uid1 = f"user_{uuid.uuid4().hex[:8]}"
    unique_uid2 = f"user_{uuid.uuid4().hex[:8]}"

    get_or_create_user(unique_uid1, f"{unique_uid1}@campus.edu", "Alice Walker")
    get_or_create_user(unique_uid2, f"{unique_uid2}@campus.edu", "Bob Vance")

    from app.services.firebase import get_db, _is_mock_db
    db = get_db()
    if _is_mock_db:
        db.users[unique_uid1]["totalGrams"] = 500.0
        db.users[unique_uid1]["totalItems"] = 10
        db.users[unique_uid2]["totalGrams"] = 800.0
        db.users[unique_uid2]["totalItems"] = 15
        db.stats["campus"]["totalGrams"] = 1300.0
        db.stats["campus"]["totalItems"] = 25
        db.stats["campus"]["countsByMaterial"]["pet_bottle"] = 20
        db.stats["campus"]["countsByMaterial"]["aluminium_can"] = 5
    else:
        db.collection("users").document(unique_uid1).update({"totalGrams": 500.0, "totalItems": 10})
        db.collection("users").document(unique_uid2).update({"totalGrams": 800.0, "totalItems": 15})

    response = client.get("/api/stats", headers={"X-Dev-User": unique_uid1})
    assert response.status_code == 200
    data = response.json()

    assert "totalGrams" in data
    assert "totalItems" in data
    assert "countsByMaterial" in data
    assert "leaderboard" in data
    assert len(data["leaderboard"]) >= 2

    # Check leaderboard privacy: no email exposed
    for entry in data["leaderboard"]:
        assert "@" not in entry["displayName"]
        assert entry["rank"] >= 1
