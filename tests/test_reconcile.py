import pytest

from tests.factories import make_gp
from orbital_catalog.reconcile import _delta, _exceeds, latest_per_object


def test_delta_standard():
    assert _delta(10.0, 7.0) == 3.0


def test_delta_none():
    assert _delta(5.0, None) is None


def test_delta_zero():
    assert _delta(5.0, 0.0) == 5.0


@pytest.mark.parametrize(
    ("delta", "published", "expected"),
    [
        (0.9, 415, False),
        (1.1, 415, True),
        (7.0, 35786, False),
        (27.0, 35786, True),
        (None, 415, None),
    ]
)
def test_exceeds(delta, published, expected):
    assert _exceeds(delta, published) is expected


@pytest.mark.parametrize("order", ["older_first", "newer_first"])
def test_latest_per_object_keeps_newest(order):
    older = make_gp(1, "2026-09-23T00:00:00")
    newer = make_gp(1, "2026-09-24T00:00:00")
    records = [older, newer] if order == "older_first" else [newer, older]
    assert latest_per_object(records) == [newer]
