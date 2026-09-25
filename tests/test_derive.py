import pytest

from orbital_catalog.derive import Orbit, apogee_perigee, classify_orbit, period_minutes, semi_major_axis

ISS_MEAN_MOTION = 15.49174705
ISS_ECCENTRICITY = 0.00069346


def test_iss_period_matches_satcat():
    assert period_minutes(ISS_MEAN_MOTION) == pytest.approx(92.95, abs=0.01)


def test_iss_semi_major_axis():
    assert semi_major_axis(ISS_MEAN_MOTION) == pytest.approx(6797.276, abs=0.01)


def test_iss_apogee_perigee():
    a = semi_major_axis(ISS_MEAN_MOTION)
    apogee, perigee = apogee_perigee(a, ISS_ECCENTRICITY)
    assert apogee == pytest.approx(424, abs=1.0)
    assert perigee == pytest.approx(415, abs=1.0)


@pytest.mark.parametrize(
    ("apogee", "perigee", "ecc", "inc", "expected"),
    [
        (424, 415, 0.0007, 51.6, Orbit.LEO),    # ISS
        (20200, 20180, 0.0005, 55.0, Orbit.MEO),  # GPS
        (35790, 35780, 0.0001, 0.05, Orbit.GEO),  # Geostationary
        (39800, 500, 0.74, 63.4, Orbit.HEO),  # Molniya
        (36100, 36080, 0.0002, 2.0, Orbit.OTHER),  # Graveyard
        (35790, 35780, 0.0002, 50.0, Orbit.OTHER),  # inclined geosynchronous (BeiDou-style)
    ],
)
def test_classify_orbit(apogee, perigee, ecc, inc, expected):
    assert classify_orbit(apogee, perigee, ecc, inc) == expected
