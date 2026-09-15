from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class GPRecord(BaseModel):
    """One row of a GP element-set CSV: one object's orbit at one moment (EPOCH)."""
    # Input: whatever the CSV hands you. Output: a validated, typed object.

    name: str = Field(alias="OBJECT_NAME")
    norad_cat_id: int = Field(alias="NORAD_CAT_ID")
    mean_motion: float = Field(alias="MEAN_MOTION")
    eccentricity: float = Field(alias="ECCENTRICITY")
    inclination: float = Field(alias="INCLINATION")
    epoch: datetime = Field(alias="EPOCH")

    @field_validator('epoch', mode="after")
    @classmethod
    def assign_timezone(cls, raw_time: datetime) -> datetime:
        if raw_time.tzinfo is None:
            return raw_time.replace(tzinfo=timezone.utc)
        return raw_time