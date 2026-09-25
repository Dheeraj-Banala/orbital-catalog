from orbital_catalog.models import GPRecord


def make_satcat(**overrides) -> dict:
    """A raw SATCAT CSV row (the ISS) as a dict of strings, NOT a validated record.

    Deliberately raw so tests can pass bad values (e.g. LAUNCH_DATE="") and assert that
    validation rejects them. Wrap in SatcatRecord.model_validate() when you need a record.
    """
    row = {
        "NORAD_CAT_ID": "25544", "OBJECT_ID": "1998-067A", "OBJECT_NAME": "ISS (ZARYA)",
        "OBJECT_TYPE": "PAY", "OWNER": "ISS", "LAUNCH_DATE": "1998-11-20",
        "PERIOD": "92.95", "APOGEE": "424", "PERIGEE": "415", "INCLINATION": "51.63",
        "DECAY_DATE": "", "ORBIT_CENTER": "EA",
    }
    row.update(overrides)
    return row


def make_gp(norad_id: int, epoch: str) -> GPRecord:
    """A validated GPRecord with fixed orbital values; only the ID and epoch vary.

    Returns a record (not a raw row) because every current caller needs one -- unlike
    make_satcat, no test yet feeds it invalid input.
    """
    return GPRecord.model_validate({
        "OBJECT_NAME": "TEST", "NORAD_CAT_ID": norad_id, "EPOCH": epoch,
        "MEAN_MOTION": 15.5, "ECCENTRICITY": 0.001, "INCLINATION": 51.6,
        "RA_OF_ASC_NODE": 0, "ARG_OF_PERICENTER": 0, "MEAN_ANOMALY": 0, "BSTAR": 0,
    })
