"""Daily Orbital Catalog pipeline: land Celestrak data, then load BigQuery.

    fetch ──► create_tables ──┬──► load_objects
                              └──► load_element_sets
"""
from datetime import date, datetime, timedelta

from airflow.sdk import dag, get_current_context, task


def _run_time() -> datetime:
    """The moment this run is *for*, in UTC. Manual runs in Airflow 3 may have no
    logical date, so fall back to when the run was requested."""
    ctx = get_current_context()
    return ctx["logical_date"] or ctx["dag_run"].run_after


def _client():
    import os
    from google.cloud import bigquery
    return bigquery.Client(project=os.environ["GCP_PROJECT"])


@dag(
    schedule="0 6 * * *",          # daily, 06:00 UTC
    start_date=datetime(2026, 9, 25),
    catchup=False,                 # don't backfill every day since start_date
    max_active_runs=1,             # never two runs writing at once
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["orbital-catalog"],
)
def orbital_catalog_daily():

    @task
    def fetch() -> str:
        import asyncio
        from airflow.sdk.exceptions import AirflowFailException
        from orbital_catalog.fetch import SourceUnavailable, fetch_all
        from orbital_catalog.sources import phase1_sources

        run_date = _run_time().date()
        try:
            asyncio.run(fetch_all(phase1_sources(), run_date=run_date))
        except SourceUnavailable as exc:
            # Celestrak policy: any non-200 means stop -- fail now, skip the retries.
            raise AirflowFailException(str(exc)) from exc
        return run_date.isoformat()

    @task
    def create_tables() -> None:
        from orbital_catalog import warehouse
        warehouse.create_tables(_client())

    @task
    def load_objects(run_date: str) -> int:
        from orbital_catalog import warehouse
        from orbital_catalog.fetch import run_dir
        from orbital_catalog.load import load_satcat_file

        satcat = load_satcat_file(run_dir(date.fromisoformat(run_date)) / "satcat_full.csv")
        loaded_at = _run_time()
        rows = [warehouse.satcat_to_row(r, loaded_at) for r in satcat.values()]
        warehouse.load_objects(_client(), rows)
        return len(rows)

    @task
    def load_element_sets(run_date: str) -> int:
        from orbital_catalog import warehouse
        from orbital_catalog.fetch import run_dir
        from orbital_catalog.load import load_gp_file, load_satcat_file
        from orbital_catalog.reconcile import latest_per_object, reconcile_all
        from orbital_catalog.sources import PHASE1_GP_GROUPS, gp_group

        run = run_dir(date.fromisoformat(run_date))
        satcat = load_satcat_file(run / "satcat_full.csv")
        gp = [r for g in PHASE1_GP_GROUPS for r in load_gp_file(run / gp_group(g).filename)]
        pairs = reconcile_all(latest_per_object(gp), satcat)
        loaded_at = _run_time()
        rows = [warehouse.element_set_to_row(g, r, loaded_at) for g, r in pairs]
        warehouse.load_element_sets(_client(), rows, loaded_at)
        return len(rows)

    run_date = fetch()
    tables = create_tables()
    run_date >> tables
    tables >> [load_objects(run_date), load_element_sets(run_date)]


orbital_catalog_daily()