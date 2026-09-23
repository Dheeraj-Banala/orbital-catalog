from datetime import datetime
from pydantic import BaseModel
from .models import GPRecord, SatcatRecord
from .derive import Orbit, period_minutes, semi_major_axis, apogee_perigee, classify_orbit


TOL_FLOOR_KM = 1.0     # SATCAT rounds apogee/perigee to whole km
TOL_FRACTION = 0.0005  # 0.05% of altitude, so the tolerance scales with orbit height


class Reconciliation(BaseModel):
    """One GP object's derived orbit compared against SATCAT's published values.
    Deltas are signed: derived minus published."""

    norad_cat_id: int
    name: str
    flagged: bool | None
    epoch: datetime
    orbit_class: Orbit

    derived_period_min: float
    derived_apogee_km: float
    derived_perigee_km: float

    satcat_period_min: float | None
    satcat_apogee_km: float | None
    satcat_perigee_km: float | None

    delta_period_min: float | None
    delta_apogee_km: float | None
    delta_perigee_km: float | None


def _delta(derived: float, published: float | None) -> float | None:
    if published is not None:
        return derived - published
    return None


def _exceeds(delta: float | None, published: float | None) -> bool | None:
    """True if the gap is past tolerance, False if within it, None if it can't be checked."""
    if delta is None or published is None:
        return None
    tolerance = max(TOL_FLOOR_KM, TOL_FRACTION * published)
    return abs(delta) > tolerance


def reconcile(gp: GPRecord, sat: SatcatRecord) -> Reconciliation:
    derived_period = period_minutes(gp.mean_motion)
    a = semi_major_axis(gp.mean_motion)
    derived_apogee, derived_perigee = apogee_perigee(a, gp.eccentricity)

    orbit = classify_orbit(derived_apogee, derived_perigee, gp.eccentricity, gp.inclination)

    delta_period = _delta(derived_period, sat.period)
    delta_apogee = _delta(derived_apogee, sat.apogee)
    delta_perigee = _delta(derived_perigee, sat.perigee)

    checks = [
        _exceeds(delta_apogee, sat.apogee),
        _exceeds(delta_perigee, sat.perigee),
    ]
    known = [c for c in checks if c is not None]
    flagged = any(known) if known else None

    return Reconciliation(
        norad_cat_id=gp.norad_cat_id,
        name=gp.name,
        flagged=flagged,
        epoch=gp.epoch,
        orbit_class=orbit,
        derived_period_min=derived_period,
        derived_apogee_km=derived_apogee,
        derived_perigee_km=derived_perigee,
        satcat_period_min=sat.period,
        satcat_apogee_km=sat.apogee,
        satcat_perigee_km=sat.perigee,
        delta_period_min=delta_period,
        delta_apogee_km=delta_apogee,
        delta_perigee_km=delta_perigee,
    )