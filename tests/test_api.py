import pytest
from fastapi.testclient import TestClient
from orbital_catalog import api
from orbital_catalog.catalog import CatalogCache
from orbital_catalog.derive import Orbit
from tests.factories import make_catalog_object

FAKE_CATALOG = [
    make_catalog_object(),                                                   # ISS: LEO, not flagged
    make_catalog_object(norad_cat_id=44713, object_name="STARLINK-1007", flagged=True),
    make_catalog_object(norad_cat_id=24876, object_name="GPS BIIR-2", orbit_class=Orbit.MEO,
                        apogee_km=20200.0, perigee_km=20150.0, flagged=None),
]


@pytest.fixture
def client():
    api.app.dependency_overrides[api.get_cache] = lambda: CatalogCache(lambda: FAKE_CATALOG)
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_get_object_returns_it(client):
    response = client.get("/objects/25544")
    assert response.status_code == 200
    assert response.json()["object_name"] == "ISS (ZARYA)"


def test_get_unknown_id(client):
    response = client.get("/objects/1")
    assert response.status_code == 404


def test_filter_by_orbit_class(client):
    response = client.get("/objects?orbit_class=LEO")
    assert response.status_code == 200
    id_list = [item["norad_cat_id"] for item in response.json()["items"]]
    assert id_list == [25544, 44713]


def test_filter_by_name_is_case_insensitive_partial_match(client):
    response = client.get("/objects?name=starlink")
    assert response.status_code == 200
    id_list = [item["norad_cat_id"] for item in response.json()["items"]]
    assert id_list == [44713]


def test_flagged_false_excludes_unflagged_and_unknown(client):
    # GPS has flagged=None (nothing to compare against), which is not the same as False.
    response = client.get("/objects?flagged=false")
    assert response.status_code == 200
    id_list = [item["norad_cat_id"] for item in response.json()["items"]]
    assert id_list == [25544]


def test_paging_counts_all_matches_and_returns_one_page(client):
    response = client.get("/objects?limit=1&offset=1")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["norad_cat_id"] for item in body["items"]] == [25544]


@pytest.mark.parametrize("query", ["orbit_class=XYZ", "limit=5000"])
def test_invalid_query_params_are_rejected(client, query):
    response = client.get(f"/objects?{query}")
    assert response.status_code == 422


def test_stats_counts_by_orbit_class(client):
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json()["by_orbit_class"] == {"LEO": 2, "MEO": 1}
