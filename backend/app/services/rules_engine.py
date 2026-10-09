from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional, Dict, Any
from app.schemas import ItemAnalysis

def calculate_points(material: str, weight_g: float, rates_per_100g: Dict[str, int]) -> int:
    """Calculate reward points based on item material and weight.
    
    Formula from PRD Section 7.4:
    points = round(weight_g / 100 * rate_per_100g)
    Uses arithmetic half-up rounding so 2.5 -> 3, 22.5 -> 23.
    """
    rate = rates_per_100g.get(material, 0)
    if rate <= 0 or weight_g <= 0:
        return 0
    val = (weight_g / 100.0) * rate
    return int(Decimal(str(val)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def check_weight_bounds(material: str, weight_g: float, weight_bounds: Dict[str, Dict[str, float]]) -> Tuple[bool, Optional[str]]:
    """Verify that simulated weight is within physical sanity bounds for the material."""
    bounds = weight_bounds.get(material)
    if not bounds:
        return True, None
    
    min_g = bounds.get("min", 0.0)
    max_g = bounds.get("max", float("inf"))

    if weight_g < min_g:
        return False, f"Weight {weight_g:.1f}g is below minimum expected weight ({min_g:.1f}g) for {material.replace('_', ' ')}."
    if weight_g > max_g:
        return False, f"Weight {weight_g:.1f}g exceeds maximum expected weight ({max_g:.1f}g) for {material.replace('_', ' ')}."
    
    return True, None

def evaluate_drop(
    analysis: ItemAnalysis,
    weight_g: float,
    config: Dict[str, Any]
) -> Tuple[bool, int, Optional[str]]:
    """Apply anti-fraud rules, vision checks, and points calculations.
    
    Returns:
        (is_accepted: bool, points: int, reject_reason: Optional[str])
    """
    rates = config.get("rates_per_100g", {})
    weight_bounds = config.get("weight_bounds_g", {})
    min_confidence = config.get("min_confidence", 0.70)

    # 1. Multiple items check
    if analysis.multiple_items:
        return False, 0, "Multiple items detected. Please drop only one item at a time."

    # 2. No recognizable item check
    if analysis.material == "no_item":
        return False, 0, analysis.reason or "No recognizable item detected in frame. Please reposition and hold item clearly."

    # 3. Non-recyclable item check
    if analysis.material == "non_recyclable":
        return False, 0, analysis.reason or "Item is classified as non-recyclable."

    # 4. Confidence threshold check
    if analysis.confidence < min_confidence:
        return False, 0, f"Confidence score ({analysis.confidence:.2f}) is below {min_confidence:.2f}. Please retake with better lighting."

    # 5. Contamination check (dirty, liquid, wet, food)
    if analysis.contaminated:
        return False, 0, analysis.reason or "Item appears contaminated or contains residue. Clean and empty item before recycling."

    # 6. Physical weight sanity bound check
    is_valid_weight, weight_err = check_weight_bounds(analysis.material, weight_g, weight_bounds)
    if not is_valid_weight:
        return False, 0, weight_err

    # 7. Points calculation
    points = calculate_points(analysis.material, weight_g, rates)
    return True, points, None
