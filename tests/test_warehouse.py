from datetime import datetime, timezone

from tests.factories import make_satcat, make_gp
from orbital_catalog.models import SatcatRecord
from orbital_catalog.reconcile import reconcile
from orbital_catalog.warehouse import satcat_to_row, element_set_to_row, OBJECTS_SCHEMA, ELEMENT_SETS_SCHEMA

def test_objects_row_matches_schema():
    record = SatcatRecord.model_validate(make_satcat())
    row = satcat_to_row(record, datetime(2026, 9, 25, tzinfo=timezone.utc))
    assert list(row) == [field.name for field in OBJECTS_SCHEMA]


def test_element_sets_row_matches_schema():
    gp = make_gp(25544, "2026-09-25T00:00:00")
    sat = SatcatRecord.model_validate(make_satcat())
    rec = reconcile(gp, sat)
    row = element_set_to_row(gp, rec, datetime(2026, 9, 25, tzinfo=timezone.utc))
    assert list(row) == [field.name for field in ELEMENT_SETS_SCHEMA]
