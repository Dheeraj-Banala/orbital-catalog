import math
from enum import StrEnum

MU = 398600.4418   # Earth's gravitational parameter, km^3/s^2
R_EARTH = 6378.137 # equatorial radius, km
LEO_MAX_ALT = 2000 # km
GEO_ALT = 35786 # km
GEO_MARGIN = 200 # km, IADC GEO protected region
GEO_MAX_INC = 15 # degrees, IADC GEO protected region
HEO_MIN_ECC = 0.25 # min eccentricity, judgement: apogee/perigee ratio of ~1.67


class Orbit(StrEnum):
    LEO = "LEO"
    MEO = "MEO"
    HEO = "HEO"
    GEO = "GEO"
    OTHER = "OTHER"


def period_minutes(mean_motion: float) -> float:
    """Accepts revolutions per day and returns minutes"""
    return 1440 / mean_motion


def semi_major_axis(mean_motion: float) -> float:
    """Orbit's semi-major axis in km, measured from Earth's CENTRE."""
    n_rad = (mean_motion * 2 * math.pi) / 86400
    return (MU / n_rad**2) ** (1/3)


def apogee_perigee(a: float, eccentricity: float) -> tuple[float, float]:
    """Apogee and perigee ALTITUDES in km, above the surface."""
    apogee_alt  = a * (1 + eccentricity) - R_EARTH
    perigee_alt = a * (1 - eccentricity) - R_EARTH
    return (apogee_alt, perigee_alt)


def classify_orbit(apogee_alt: float, perigee_alt: float, eccentricity: float, inclination: float) -> Orbit:
    if eccentricity > HEO_MIN_ECC:
        return Orbit.HEO
    elif (
        inclination <= GEO_MAX_INC
        and abs(perigee_alt - GEO_ALT) <= GEO_MARGIN
        and abs(apogee_alt - GEO_ALT) <= GEO_MARGIN
    ):
        return Orbit.GEO
    elif apogee_alt <= LEO_MAX_ALT:
        return Orbit.LEO
    elif perigee_alt > LEO_MAX_ALT and apogee_alt < GEO_ALT - GEO_MARGIN:
        return Orbit.MEO
    else:
        return Orbit.OTHER
