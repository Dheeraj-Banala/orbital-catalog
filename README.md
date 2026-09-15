# Orbital Object Catalog

A backend service over a catalog of everything humans have put in Earth orbit — live
satellites, dead ones, spent rocket bodies, and debris — kept current by a scheduled
ingestion pipeline.

**Status: Phase 1 (raw ingestion).** Not yet a service. See [Roadmap](#roadmap).

## Architecture (target)

```
Airflow DAG (scheduled, retries)                     FastAPI service
  async fetch ──► transform ──► BigQuery ───────────► REST API ──► client
   (Celestrak)    (parse/derive/                        (+ cache)
                   reconcile)
                  all under one docker compose
```

## Data sources

Both from [CelesTrak](https://celestrak.org), joined on `NORAD_CAT_ID`.

| Source | What it is | Shape |
|---|---|---|
| **GP element sets** (`gp.php?GROUP=…`) | Orbital elements — the parameters describing each object's orbit. Served per group (`stations`, `gps-ops`, `geo`, `starlink`, …). | ~30 group endpoints, updated every 2h |
| **SATCAT** (`pub/satcat.csv`) | Catalog metadata — owner, launch date, object type, operational status, decay date. | 70,122 rows; 34,726 still on orbit |

Catalog composition as of 2026-07-26: 27,258 payloads · 35,833 debris · 6,870 rocket
bodies · 161 unknown. Roughly half of all catalogued objects have already decayed.

### Playing nice with CelesTrak

CelesTrak is a free public service and [enforces its usage
policy](https://celestrak.org/usage-policy.php) — this is not advisory. Encoded in
`orbital_catalog/fetch.py`:

- **Download once per update, not once per run.** Files land in `data/raw/<utc-date>/`
  and a same-day file already on disk is a cache hit, not a re-fetch. Every later stage
  replays from the landing zone rather than the network.
- **Stop on any non-200.** No retry loop. CelesTrak returns `403` on a repeat pull of
  data that hasn't changed and asks machine clients to back off, not hammer.
- **Identify yourself** in the `User-Agent`.
- `GROUP=active` and `GROUP=starlink` have the strictest enforcement and are deliberately
  excluded until caching is proven.

## Running it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
.venv/Scripts/python scripts/fetch_raw.py
```

Requires a `.env` with `CELESTRAK_CONTACT=you@example.com` — an address you actually
monitor. CelesTrak asks automated clients to be reachable, and that's how they'd contact
you before blocking a misbehaving pipeline. The fetcher refuses to run without it.

`--force` re-downloads over the cache. For fixing a truncated file, not for iterating.

## Design decisions

**Why a landing zone instead of parsing inline.** Raw responses are written to disk
untouched before anything reads them. Parsing, deriving, and loading all replay from
those files. This keeps development off the network (the usage policy makes that a
requirement, not a preference), and it means a transform bug is a re-run rather than
a re-fetch.

**Why the transform reconciles instead of just deriving.** SATCAT already publishes
`PERIOD`, `APOGEE`, `PERIGEE`, and `INCLINATION`. Copying those columns would make this
a file-format converter. Instead the pipeline derives the same quantities independently
from the GP element sets (mean motion → period; mean motion + eccentricity → apogee and
perigee) and reconciles the two sources, flagging disagreement beyond a tolerance. Two
sources describing the same object, resolved into one record, is the actual work.

**Why `httpx` and not `requests`.** Phase 3 converts the extract step to concurrent
async fetching across the group endpoints. `httpx` makes that a `Client` → `AsyncClient`
change rather than a rewrite.

**Why the full `satcat.csv` and not the query API.** `records.php` requires a `GROUP`,
and only offers `active` and `analyst`. `active` returns ~16.6K rows that are 99.99%
payloads — no debris, no rocket bodies. Since "how much of what's up there is junk" is a
question this service should answer, the filtered view can't serve it.

## Roadmap

- [x] **Phase 1** — Verify sources; land raw data. Plain Python, no infra.
- [ ] **Phase 2** — Parse GP element sets, derive orbital parameters, reconcile against
      SATCAT, model and load the BigQuery schema.
- [ ] **Phase 3** — Concurrent async extraction (`asyncio` + `httpx`) across group
      endpoints, with backoff and partial-failure handling.
- [ ] **Phase 4** — Containerize (`docker compose`).
- [ ] **Phase 5** — Airflow DAG: dependencies, retries, scheduling, failure alerting.
- [ ] **Phase 6** — pytest over the transform logic; GitHub Actions CI.
- [ ] **Phase 7** — FastAPI service: filter by owner, orbit class, altitude, object type.
- [ ] **Phase 8** — Architecture diagram and design writeup.
- [ ] **Phase 9** *(stretch)* — `sgp4` propagation: compute live positions from stored
      elements. Until this ships, this is a **catalog**, not a tracker.
