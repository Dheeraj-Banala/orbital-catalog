from datetime import timezone

import pytest
from pydantic import ValidationError

from tests.factories import make_gp, make_satcat
from orbital_catalog.models import SatcatRecord


def test_naive_epoch_becomes_utc_without_shifting():
    record = make_gp(1, "2026-07-26T02:07:09")
    assert record.epoch.tzinfo == timezone.utc
    assert record.epoch.hour == 2


def test_satcat_blanks_become_none():
    row = make_satcat(PERIOD="", DECAY_DATE="")
    record = SatcatRecord.model_validate(row)
    assert record.period is None
    assert record.decay_date is None


def test_blank_launch_date_fails_loudly():
    with pytest.raises(ValidationError):
        SatcatRecord.model_validate(make_satcat(LAUNCH_DATE=""))
