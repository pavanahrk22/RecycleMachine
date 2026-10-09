from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

MaterialType = Literal[
    "pet_bottle",
    "aluminium_can",
    "rigid_plastic",
    "snack_wrapper",
    "non_recyclable",
    "no_item"
]

class ItemAnalysis(BaseModel):
    """Structured response parsed directly from Gemini vision API."""
    material: str = Field(
        description="One of: pet_bottle, aluminium_can, rigid_plastic, snack_wrapper, non_recyclable, no_item"
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0"
    )
    contaminated: bool = Field(
        description="True if visibly dirty, wet, or containing liquid, food, or foreign objects"
    )
    multiple_items: bool = Field(
        description="True if more than one item is visible in the frame"
    )
    reason: str = Field(
        description="One short sentence explaining the classification or rejection rationale"
    )

class DropResponse(BaseModel):
    """Response returned to client after item classification and validation."""
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["accepted", "rejected"]
    material: str
    confidence: float
    weight_g: float = Field(alias="weightG")
    points: int
    reject_reason: Optional[str] = Field(default=None, alias="rejectReason")
    new_balance: Optional[int] = Field(default=None, alias="newBalance")
    machine_id: str = Field(alias="machineId")

class HealthResponse(BaseModel):
    status: str
    service: str
