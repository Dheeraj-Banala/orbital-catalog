from datetime import date

import pytest

from orbital_catalog.fetch import can_fetch

TODAY = date(2026, 9, 25)
PAST = date(2026, 9, 22)


@pytest.mark.parametrize(
    "run_date, all_landed, expected",
    [
        (TODAY, False, True),   # daily run, nothing landed yet → allowed
        (TODAY, True,  True),   # same-day rerun, files already there
        (PAST,  True,  True),   # rerun of a past day that fully landed
        (PAST,  False, False),  # past day with files missing (the bug)
    ],
    ids=["today-empty", "today-rerun", "past-landed", "past-missing"],
)
def test_can_fetch(run_date, all_landed, expected):
    assert can_fetch(run_date, TODAY, all_landed) is expected
