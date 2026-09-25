from datetime import date, datetime, timedelta, timezone
from collections.abc import Callable
import logging

from pydantic import BaseModel
from google.cloud import bigquery

from .derive import Orbit
from .warehouse import table_id


log = logging.getLogger(__name__)


CATALOG_QUERY = """
SELECT
  norad_cat_id, object_id, object_name, object_type, owner, launch_date,
  orbit_class, epoch, inclination_deg, eccentricity,
  derived_period_min AS period_min,
  derived_apogee_km  AS apogee_km,
  derived_perigee_km AS perigee_km,
  apogee_km          AS satcat_apogee_km,
  perigee_km         AS satcat_perigee_km,
  flagged
FROM `{view}`
"""


class CatalogObject(BaseModel):
    """One object as the API returns it: identity from SATCAT, orbit from the newest element set.

    apogee_km / perigee_km / period_min are our values, derived from the element set.
    satcat_* are the published values they were reconciled against.
    """

    norad_cat_id: int
    object_id: str
    object_name: str
    object_type: str               # PAY, R/B, DEB or UNK
    owner: str | None
    launch_date: date | None
    orbit_class: Orbit
    epoch: datetime
    inclination_deg: float
    eccentricity: float
    period_min: float
    apogee_km: float
    perigee_km: float
    satcat_apogee_km: float | None
    satcat_perigee_km: float | None
    flagged: bool | None           # None = no published value to compare against


def fetch_catalog(client: bigquery.Client) -> list[CatalogObject]:
    """Every object in current_catalog, as API models. One BigQuery query."""
    sql = CATALOG_QUERY.format(view=table_id("current_catalog"))
    rows = client.query(sql).result()
    return [CatalogObject.model_validate(dict(row)) for row in rows]


class CatalogCache:
    """The catalog held in memory, keyed by NORAD ID, reloaded when older than max_age."""

    def __init__(self, loader: Callable[[], list[CatalogObject]], max_age: timedelta = timedelta(hours=6)):
        self._loader = loader
        self._max_age = max_age
        self._objects: dict[int, CatalogObject] = {}
        self.loaded_at: datetime | None = None

    def objects(self) -> dict[int, CatalogObject]:
        """The current catalog, refreshing first if it's stale."""
        # YOU: if never loaded, or older than max_age -> call self.refresh()
        if self.loaded_at is None or datetime.now(timezone.utc) - self.loaded_at > self._max_age:
            self.refresh()
        return self._objects

    def refresh(self) -> None:
        try:
            fresh = self._loader()
        except Exception:
            if self.loaded_at is None:
                raise
            log.warning("Catalog refresh failed; serving data from %s", self.loaded_at, exc_info=True)
            return

        new_dict = {item.norad_cat_id: item for item in fresh}
        self._objects = new_dict
        self.loaded_at = datetime.now(tz=timezone.utc)
