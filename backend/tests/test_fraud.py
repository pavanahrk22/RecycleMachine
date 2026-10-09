from datetime import datetime, timezone, timedelta
from app.services.firebase import InMemoryFirestore, check_fraud_and_limits
from app.config import get_rates_config

def test_fraud_duplicate_image_within_24h(monkeypatch):
    mock_db = InMemoryFirestore()
    monkeypatch.setattr("app.services.firebase.get_db", lambda: mock_db)
    monkeypatch.setattr("app.services.firebase._is_mock_db", True)

    config = {
        "cooldown_seconds": 12,
        "daily_caps": { "max_drops": 30, "max_grams": 1000.0 }
    }

    uid = "fraud_tester"
    img_hash = "abcdef1234567890abcdef1234567890"

    # Add a drop from 2 hours ago
    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    mock_db.drops["drop_1"] = {
        "id": "drop_1",
        "uid": uid,
        "imageHash": img_hash,
        "createdAt": past_time,
        "status": "accepted",
        "weightG": 20.0
    }

    # Now attempt same hash
    valid, reason = check_fraud_and_limits(uid, img_hash, 20.0, config)
    assert valid is False
    assert "Duplicate image detected" in reason

def test_fraud_daily_cap_max_drops(monkeypatch):
    mock_db = InMemoryFirestore()
    monkeypatch.setattr("app.services.firebase.get_db", lambda: mock_db)
    monkeypatch.setattr("app.services.firebase._is_mock_db", True)

    config = {
        "cooldown_seconds": 0,
        "daily_caps": { "max_drops": 3, "max_grams": 1000.0 }
    }

    uid = "heavy_recycler"
    # Seed 3 drops within 24h
    now = datetime.now(timezone.utc)
    for i in range(3):
        t = (now - timedelta(minutes=i * 10 + 1)).isoformat()
        mock_db.drops[f"drop_{i}"] = {
            "id": f"drop_{i}",
            "uid": uid,
            "imageHash": f"hash_{i}",
            "createdAt": t,
            "status": "accepted",
            "weightG": 10.0
        }

    # 4th drop should be rejected
    valid, reason = check_fraud_and_limits(uid, "new_hash", 10.0, config)
    assert valid is False
    assert "Daily limit of 3 drops reached" in reason

def test_fraud_daily_cap_max_grams(monkeypatch):
    mock_db = InMemoryFirestore()
    monkeypatch.setattr("app.services.firebase.get_db", lambda: mock_db)
    monkeypatch.setattr("app.services.firebase._is_mock_db", True)

    config = {
        "cooldown_seconds": 0,
        "daily_caps": { "max_drops": 30, "max_grams": 100.0 }
    }

    uid = "heavy_weight_user"
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    mock_db.drops["drop_big"] = {
        "id": "drop_big",
        "uid": uid,
        "imageHash": "hash_big",
        "createdAt": past_time,
        "status": "accepted",
        "weightG": 90.0
    }

    # Adding 20g exceeds 100g limit (90 + 20 = 110)
    valid, reason = check_fraud_and_limits(uid, "new_hash", 20.0, config)
    assert valid is False
    assert "Daily limit of 100g reached" in reason
