from datetime import datetime

from airflow.sdk import dag, task


@dag(schedule=None, start_date=datetime(2026, 9, 1), catchup=False, tags=["orbital-catalog"])
def smoke_test():
    """Proves Airflow can run project code and reach BigQuery. Trigger by hand."""

    @task
    def iss_period() -> float:
        from orbital_catalog.derive import period_minutes
        return period_minutes(15.49174705)

    @task
    def list_datasets() -> list[str]:
        import os
        from google.cloud import bigquery
        client = bigquery.Client(project=os.environ["GCP_PROJECT"])
        return [d.dataset_id for d in client.list_datasets()]

    iss_period() >> list_datasets()


smoke_test()