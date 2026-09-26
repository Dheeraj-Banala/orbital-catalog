# Orbital Object Catalog

A data pipeline that keeps a queryable catalog of objects in Earth orbit: working satellites, dead ones,
spent rocket bodies and debris. It pulls public data from CelesTrak every day, derives each object's orbit
independently, checks those numbers against the published catalog, and loads the result into BigQuery.
The whole thing runs on a schedule under Apache Airflow in Docker.

## What's in it

As of the 2026-09-25 run:

| | Count |
|---|---|
| Objects ever catalogued | 70,804 |
| Still in orbit | 35,190 |
| ...of which payloads | 20,155 |
| ...debris | 12,547 |
| ...rocket bodies | 2,432 |
| Objects with current orbital elements | 16,749 |
| ...of which Starlink | 11,134 |

About 43% of what's still in orbit is debris or spent rocket bodies. Starlink alone is two thirds of all
active satellites.

This is a **catalog, not a tracker**. It stores each object's orbital elements and derived orbit shape.
It does not compute where an object is at a given moment.

## Architecture

```
                 Airflow DAG, daily at 06:00 UTC (docker compose)
  +---------------------------------------------------------------------------+
  |                                                                           |
  |  fetch  ---->  create_tables  ---->  load_objects       (SATCAT)          |
  |    |                         \                                            |
  |    |                          --->  load_element_sets   (GP + reconcile)  |
  |    v                                        |                             |
  |  data/raw/<date>/  (landing zone)           v                             |
  |                                  BigQuery: objects, element_sets,         |
  |                                            current_catalog (view)         |
  +---------------------------------------------------------------------------+
```

1. **fetch** downloads 6 GP element-set groups and the full SATCAT file concurrently, at most 3 requests
   at a time, into a folder for the run's date. Files already on disk for that date are not downloaded
   again.
2. **create_tables** makes sure the BigQuery tables exist and rebuilds the view.
3. **load_objects** replaces the `objects` table with the day's SATCAT snapshot.
4. **load_element_sets** parses the element sets, keeps the newest one per object, derives each orbit,
   reconciles it against SATCAT and writes the day's rows. The two loads run in parallel.

## Data sources

Both come from [CelesTrak](https://celestrak.org) and join on `NORAD_CAT_ID`.

| Source | What it is |
|---|---|
| GP element sets (`gp.php?GROUP=...&FORMAT=csv`) | The parameters that describe each object's orbit: mean motion, eccentricity, inclination, epoch and so on. Served per group. This project pulls `active`, `stations`, `gps-ops`, `visual`, `weather` and `geo`. |
| SATCAT (`pub/satcat.csv`) | Catalog metadata for every object ever tracked: type, owner, launch date, decay date, plus CelesTrak's published period, apogee, perigee and inclination. |

The full `satcat.csv` is used instead of the query API because the query API only offers the `active`
group, which is almost all payloads. Debris and rocket bodies are half of the interesting data, so the
filtered view can't answer "how much of what's up there is junk."

## Deriving and reconciling

The GP element sets and SATCAT both describe each object's orbit, but they're updated on different cycles,
and SATCAT's published period, apogee and perigee can lag behind what the object is actually doing. The
pipeline derives those values from the latest elements and reconciles them against SATCAT, so every object
carries a record of whether the two sources agree and by how much.

From mean motion *n* (revolutions per day) and eccentricity *e*:

- period = 1440 / *n* minutes
- semi-major axis *a* = (mu / n_rad^2)^(1/3), with *n* converted to radians per second
- apogee and perigee altitude = *a*(1 + *e*) - R_earth and *a*(1 - *e*) - R_earth

For the ISS this gives a 92.95 minute period and 423.9 / 414.4 km, against SATCAT's 92.95 and 424 / 415.

**Tolerance.** An object is flagged when its derived apogee or perigee differs from SATCAT's by more than
the larger of **1 km** or **0.05% of the published altitude**:

- The 1 km floor exists because SATCAT rounds altitudes to whole kilometres. The median disagreement is
  0.2 to 0.3 km in every orbit class, which is mostly that rounding. A tighter tolerance would flag noise.
- The 0.05% term scales with height. 5 km is a real change at 262 km but ordinary station-keeping at the
  geostationary belt, where 0.05% works out to about 18 km.
- Period isn't checked separately. It comes from the same mean motion as the altitudes, so it adds no
  information.
- `flagged` has three states. `NULL` means SATCAT had no published value to compare against, which is not
  the same as passing.

**What the flags catch.** The large disagreements aren't derivation errors. They're the two sources
describing the object at different times:

- In the 2026-07-26 data, the satellite CORAL was flagged with a perigee 5.75 km below SATCAT's value.
  SATCAT lists it as having re-entered on 2026-08-01, six days later. It was decaying and the published
  value hadn't caught up.
- USA 270 and USA 271, two military satellites in the geostationary belt, show gaps of 7 to 250 km across
  runs. Satellites that maneuver change their orbit between the two sources' updates.
- In the 2026-09-25 run, 775 of 16,749 objects are flagged, almost all in low orbit. The largest gaps are
  Starlink satellites more than 100 km below their published altitude.

**Orbit classes** (checked in this order, first match wins): HEO if eccentricity > 0.25, GEO if both
apogee and perigee are within 200 km of 35,786 km with inclination under 15 degrees (the IADC's GEO
protected region), LEO if apogee is at or below 2,000 km (the IADC's LEO region), MEO if it sits between
the two, and OTHER for everything else. HEO goes first so an orbit like Molniya (perigee around 500 km,
apogee around 39,000 km) isn't misread by the altitude rules. OTHER covers about 60 objects today, such as
graveyard orbits just above the GEO belt and geosynchronous satellites with too much inclination to count
as geostationary.

## Warehouse

BigQuery dataset `orbital_catalog`:

| Table | One row per | How it's loaded |
|---|---|---|
| `objects` | object (SATCAT) | Replaced in full each run. SATCAT is a complete snapshot, so there is nothing to merge. |
| `element_sets` | object per run date | Partitioned by day on `loaded_at`. Each run overwrites only its own day's partition. |
| `current_catalog` (view) | object still in orbit | Each object joined to its newest element set, excluding objects SATCAT lists as decayed. |

Identity and orbits live in separate tables because they change at different rates: an object's owner and
launch date almost never change, while its orbit is updated every few hours. `element_sets` keeps history,
so you can see how an orbit changed over time.

**Reruns are safe.** `loaded_at` is the run's logical date from Airflow, not the wall-clock time, and each
load writes to that day's partition (`element_sets$YYYYMMDD`) with `WRITE_TRUNCATE`. Rerunning Tuesday's run
on Thursday replaces Tuesday's rows, from Tuesday's landed files, and leaves every other day alone. BigQuery
doesn't enforce unique keys, so this is how duplicates are prevented. It uses load jobs only, which BigQuery
doesn't charge for, rather than streaming inserts or `MERGE`. If Tuesday's files never fully landed, the run
fails instead: CelesTrak only serves current data, so fetching on Thursday would file Thursday's data under
Tuesday.

## Orchestration

`dags/orbital_catalog_daily.py`:

- Runs daily at 06:00 UTC. `catchup=False`, so enabling it doesn't backfill every day since the start date.
- `max_active_runs=1`, so two runs never write to the warehouse at once.
- Every task retries twice, 5 minutes apart, except that a CelesTrak refusal fails the fetch immediately.
- Tasks pass only the run date between them. Each task reads the files it needs from that date's folder,
  rather than pushing thousands of rows through Airflow's metadata database.

Airflow runs from a trimmed copy of the official Airflow 3.3.2 compose file. The official file uses the
Celery executor with Redis and a separate worker, which is built for spreading tasks over many machines.
This project runs on one machine with a handful of tasks a day, so it uses `LocalExecutor` and drops Redis,
the worker and Flower.

## Running it

**Prerequisites:** Python 3.11, Docker Desktop, the Google Cloud CLI, and a GCP project with BigQuery
enabled and a dataset created.

1. Log in to Google Cloud so the client libraries can find your credentials. No key file is created:
   ```bash
   gcloud auth application-default login
   ```
2. Create a `.env` in the repo root (it's gitignored):
   ```
   CELESTRAK_CONTACT=you@example.com
   GCP_PROJECT=your-project-id
   BQ_DATASET=orbital_catalog
   GCLOUD_ADC=/full/path/to/gcloud/application_default_credentials.json
   AIRFLOW_UID=50000
   FERNET_KEY=<generate one, see below>
   ```
   `GCLOUD_ADC` is `%APPDATA%/gcloud/application_default_credentials.json` on Windows and
   `~/.config/gcloud/application_default_credentials.json` on macOS and Linux, written as a full path.
   Generate `FERNET_KEY` with:
   ```bash
   docker run --rm apache/airflow:3.3.2-python3.11 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. Start Airflow:
   ```bash
   docker compose -f airflow.compose.yaml up airflow-init
   docker compose -f airflow.compose.yaml up -d
   ```
   Open http://localhost:8080 (local default login `airflow` / `airflow`), switch on
   `orbital_catalog_daily` and trigger it.

The pipeline can also run step by step without Airflow, using the `pipeline` service in `compose.yaml`:

```bash
docker compose run --rm pipeline python scripts/fetch_raw.py
docker compose run --rm pipeline python scripts/create_tables.py
docker compose run --rm pipeline python scripts/load_objects.py
docker compose run --rm pipeline python scripts/load_element_sets.py
```

`scripts/reconcile_report.py` prints the per-class reconciliation summary and the largest disagreements
without touching BigQuery.

### Credentials

Nothing secret goes into an image. `.dockerignore` keeps `.env`, `data/` and the virtualenv out of the build.
At runtime, compose passes `.env` in as environment variables and mounts the gcloud credentials file
read-only. The same images run on any machine, and each machine's `.env` says where its own credentials are.

## Tests

```bash
pip install -r requirements.txt -r requirements-test.txt
pytest
```

24 tests over the pure functions: the derivations against SATCAT's published values, one classifier case per
orbit class, the reconciliation rules (including a regression test for treating a published value of `0.0`
as missing), dedup in both input orders, the model validation rules, and a check that each row converter's
keys match its BigQuery schema column for column. A column added to a schema but not to its converter
would otherwise load as silent `NULL`s.

The tests never touch the network or BigQuery, so GitHub Actions runs them on every push with no credentials.

## Design decisions

- **Landing zone before parsing.** Raw responses are saved untouched, and every later step replays from them.
  A transform bug means a re-run, not a re-download, and development never hits CelesTrak.
- **Following CelesTrak's [usage policy](https://celestrak.org/usage-policy.php).** It returns 403 on repeat
  downloads of unchanged data, so each file is fetched once per day and any non-200 stops the run with no
  retry. Requests identify themselves with a contact address from `CELESTRAK_CONTACT`. `starlink` isn't
  pulled as its own group because it's a subset of `active`.
- **CSV instead of TLE.** CelesTrak serves the same elements as CSV. Parsing the structured format beats
  hand-parsing a fixed-width legacy one.
- **BigQuery.** Loads are free and this dataset fits well inside the free tier. Snowflake was considered, but
  its free option is a 30-day trial, which would have left the project unrunnable after a month.
- **`asyncio.TaskGroup` rather than `gather`.** When one download fails, a `TaskGroup` cancels the others,
  which is what "stop on any non-200" requires. Files that finished are kept, and the next run's cache check
  skips them, so a rerun picks up where the last one stopped.
- **Code mounted into Airflow, not copied.** During development an edit takes effect on the next task run
  with no rebuild. A production setup would bake the code into the image so each deployment is a fixed
  version.
- **One Python version everywhere.** The virtualenv, the pipeline image and the Airflow image all use 3.11.
  Project dependencies are installed into the Airflow image together with the pinned Airflow version, and
  `pip check` is run after every change. Pinning `httpx` too old once broke packages that ship with Airflow
  without failing the build.

## Limitations

- Runs locally only. There's no hosted deployment, and the Airflow setup is the development compose file,
  not a production one.
- Orbital elements are pulled for active satellites and a few curated groups (about 16,700 objects), not
  every tracked object. Debris is in the catalog but mostly has no element set here.
- The daily schedule only runs while the machine and Docker are up. Missed days are not backfilled.
