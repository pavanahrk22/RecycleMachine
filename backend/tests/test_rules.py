import pytest
from app.config import get_rates_config
from app.schemas import ItemAnalysis
from app.services.rules_engine import calculate_points, check_weight_bounds, evaluate_drop

@pytest.fixture
def sample_config():
    return {
        "rates_per_100g": {
            "pet_bottle": 100,
            "aluminium_can": 150,
            "rigid_plastic": 80,
            "snack_wrapper": 50,
            "non_recyclable": 0,
            "no_item": 0
        },
        "weight_bounds_g": {
            "pet_bottle": { "min": 8.0, "max": 60.0 },
            "aluminium_can": { "min": 8.0, "max": 25.0 },
            "rigid_plastic": { "min": 5.0, "max": 150.0 },
            "snack_wrapper": { "min": 1.0, "max": 12.0 }
        },
        "min_confidence": 0.70
    }

def test_points_calculation_formula(sample_config):
    rates = sample_config["rates_per_100g"]
    
    # 20g PET bottle at 100 pts/100g = 20 points
    assert calculate_points("pet_bottle", 20.0, rates) == 20

    # 15g Aluminium can at 150 pts/100g = 22.5 -> rounds to 23 points
    assert calculate_points("aluminium_can", 15.0, rates) == 23
    # 20g Aluminium can at 150 pts/100g = 30 points
    assert calculate_points("aluminium_can", 20.0, rates) == 30

    # 5g snack wrapper at 50 pts/100g = 2.5 -> rounds to 3 points
    assert calculate_points("snack_wrapper", 5.0, rates) == 3

    # Non-recyclable = 0 points
    assert calculate_points("non_recyclable", 50.0, rates) == 0

def test_weight_bounds_validation(sample_config):
    bounds = sample_config["weight_bounds_g"]

    # In bounds: 20g bottle
    valid, err = check_weight_bounds("pet_bottle", 20.0, bounds)
    assert valid is True
    assert err is None

    # Too light: 4g bottle (under 8g)
    valid, err = check_weight_bounds("pet_bottle", 4.0, bounds)
    assert valid is False
    assert "below minimum expected weight" in err

    # Too heavy: 80g bottle (over 60g)
    valid, err = check_weight_bounds("pet_bottle", 80.0, bounds)
    assert valid is False
    assert "exceeds maximum expected weight" in err

    # In bounds: 15g can
    valid, err = check_weight_bounds("aluminium_can", 15.0, bounds)
    assert valid is True

    # Too heavy: 30g can (over 25g)
    valid, err = check_weight_bounds("aluminium_can", 30.0, bounds)
    assert valid is False

def test_evaluate_drop_valid_item(sample_config):
    analysis = ItemAnalysis(
        material="pet_bottle",
        confidence=0.92,
        contaminated=False,
        multiple_items=False,
        reason="Clean plastic PET bottle identified."
    )
    is_accepted, points, reason = evaluate_drop(analysis, 25.0, sample_config)
    assert is_accepted is True
    assert points == 25
    assert reason is None

def test_evaluate_drop_rejects_contaminated(sample_config):
    analysis = ItemAnalysis(
        material="pet_bottle",
        confidence=0.88,
        contaminated=True,
        multiple_items=False,
        reason="Bottle contains liquid residue."
    )
    is_accepted, points, reason = evaluate_drop(analysis, 20.0, sample_config)
    assert is_accepted is False
    assert points == 0
    assert "Bottle contains liquid residue." in reason

def test_evaluate_drop_rejects_multiple_items(sample_config):
    analysis = ItemAnalysis(
        material="pet_bottle",
        confidence=0.85,
        contaminated=False,
        multiple_items=True,
        reason="Two bottles visible in chute."
    )
    is_accepted, points, reason = evaluate_drop(analysis, 40.0, sample_config)
    assert is_accepted is False
    assert points == 0
    assert "Multiple items detected" in reason

def test_evaluate_drop_rejects_low_confidence(sample_config):
    analysis = ItemAnalysis(
        material="pet_bottle",
        confidence=0.55,
        contaminated=False,
        multiple_items=False,
        reason="Unclear blurry item."
    )
    is_accepted, points, reason = evaluate_drop(analysis, 20.0, sample_config)
    assert is_accepted is False
    assert points == 0
    assert "below 0.70" in reason

def test_evaluate_drop_rejects_non_recyclable(sample_config):
    analysis = ItemAnalysis(
        material="non_recyclable",
        confidence=0.95,
        contaminated=False,
        multiple_items=False,
        reason="Styrofoam cup is not recyclable in this machine."
    )
    is_accepted, points, reason = evaluate_drop(analysis, 15.0, sample_config)
    assert is_accepted is False
    assert points == 0
    assert "not recyclable" in reason.lower()
