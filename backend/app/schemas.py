from typing import Optional, Literal, List, Dict, Any
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

class UserProfile(BaseModel):
    """User account details and points balance."""
    model_config = ConfigDict(populate_by_name=True)

    uid: str
    email: Optional[str] = None
    display_name: Optional[str] = Field(default=None, alias="displayName")
    points_balance: int = Field(default=0, alias="pointsBalance")
    total_grams: float = Field(default=0.0, alias="totalGrams")
    total_items: int = Field(default=0, alias="totalItems")
    created_at: Optional[str] = Field(default=None, alias="createdAt")

class DropRecord(BaseModel):
    """Historical record of a drop."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    uid: str
    machine_id: str = Field(alias="machineId")
    material: str
    confidence: float
    contaminated: bool
    weight_g: float = Field(alias="weightG")
    points: int
    status: Literal["accepted", "rejected"]
    reject_reason: Optional[str] = Field(default=None, alias="rejectReason")
    image_hash: str = Field(alias="imageHash")
    created_at: str = Field(alias="createdAt")

class DropsListResponse(BaseModel):
    drops: List[DropRecord]
    total: int

class HealthResponse(BaseModel):
    status: str
    service: str
