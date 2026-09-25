import os
from collections import Counter
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query
from google.cloud import bigquery
from pydantic import BaseModel

from .catalog import CatalogCache, CatalogObject, fetch_catalog
from .derive import Orbit

app = FastAPI(title="Orbital Object Catalog")


class ObjectPage(BaseModel):
    total: int                      # how many matched, before paging
    items: list[CatalogObject]


@lru_cache
def get_cache() -> CatalogCache:
    """The one shared cache. Built on first request, not at import."""
    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    return CatalogCache(lambda: fetch_catalog(client))


@app.get("/objects/{norad_cat_id}", response_model=CatalogObject)
def get_object(norad_cat_id: int, cache: CatalogCache = Depends(get_cache)):
    obj = cache.objects().get(norad_cat_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"No object with NORAD ID {norad_cat_id}")
    return obj


@app.get("/health")
def get_health(cache: CatalogCache = Depends(get_cache)):
    objects = cache.objects()
    return {"status": "ok", "objects": len(objects), "loaded_at": cache.loaded_at}


@app.get("/objects", response_model=ObjectPage)
def list_objects(
    orbit_class: Orbit | None = None,
    object_type: str | None = None,
    owner: str | None = None,
    name: str | None = None,
    flagged: bool | None = None,
    min_perigee_km: float | None = None,
    max_apogee_km: float | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    cache: CatalogCache = Depends(get_cache),
):
    matches = []
    for o in cache.objects().values():
        if orbit_class is not None and o.orbit_class != orbit_class:
            continue
        if object_type is not None and o.object_type != object_type:
            continue
        if name is not None and name.lower() not in o.object_name.lower():
            continue
        if owner is not None and o.owner != owner:
            continue
        if flagged is not None and o.flagged != flagged:
            continue
        if min_perigee_km is not None and o.perigee_km < min_perigee_km:
            continue
        if max_apogee_km is not None and o.apogee_km > max_apogee_km:
            continue
        matches.append(o)

    matches.sort(key=lambda o: o.norad_cat_id)
    return ObjectPage(total=len(matches), items=matches[offset : offset + limit])


@app.get("/stats")
def get_stats(cache: CatalogCache = Depends(get_cache)):
    objects = cache.objects().values()
    return {
        "total": len(objects),
        "by_object_type": Counter(o.object_type for o in objects),
        "by_orbit_class": Counter(o.orbit_class for o in objects),
    }