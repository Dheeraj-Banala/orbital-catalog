from datetime import date, datetime, timezone
from pydantic import BaseModel, Field, field_validator


class GPRecord(BaseModel):
    """One row of a GP element-set CSV: one object's orbit at one moment (EPOCH)."""

    name: str = Field(alias="OBJECT_NAME")
    norad_cat_id: int = Field(alias="NORAD_CAT_ID")
    mean_motion: float = Field(alias="MEAN_MOTION")
    eccentricity: float = Field(alias="ECCENTRICITY")
    inclination: float = Field(alias="INCLINATION")
    ra_of_asc_node: float = Field(alias="RA_OF_ASC_NODE")
    arg_of_pericenter: float = Field(alias="ARG_OF_PERICENTER")
    mean_anomaly: float = Field(alias="MEAN_ANOMALY")
    bstar: float = Field(alias="BSTAR")
    epoch: datetime = Field(alias="EPOCH")

    @field_validator('epoch', mode="after")
    @classmethod
    def assign_timezone(cls, raw_time: datetime) -> datetime:
        if raw_time.tzinfo is None:
            return raw_time.replace(tzinfo=timezone.utc)
        return raw_time


class SatcatRecord(BaseModel):
    """One row of SATCAT: static metadata about one catalogued object"""

    norad_cat_id: int = Field(alias="NORAD_CAT_ID")
    object_id: str = Field(alias="OBJECT_ID")
    object_name: str = Field(alias="OBJECT_NAME")
    object_type: str = Field(alias="OBJECT_TYPE")
    owner: str = Field(alias="OWNER")
    launch_date: date = Field(alias="LAUNCH_DATE")
    period: float | None = Field(alias="PERIOD")
    apogee: float | None = Field(alias="APOGEE")
    perigee: float | None = Field(alias="PERIGEE")
    inclination: float | None = Field(alias="INCLINATION")
    decay_date: date | None = Field(alias="DECAY_DATE")
    orbit_center: str = Field(alias="ORBIT_CENTER")

    @field_validator('period', 'apogee', 'perigee', 'inclination', 'decay_date', mode="before")
    @classmethod
    def normalize_nulls(cls, raw_str: str) -> str | None:
        if raw_str == "":
            return None
        return raw_str
