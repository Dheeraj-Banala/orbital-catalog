import os
from datetime import datetime
from google.cloud import bigquery
from .models import SatcatRecord

OBJECTS_SCHEMA = [
    bigquery.SchemaField("norad_cat_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("object_id", "STRING"),
    bigquery.SchemaField("object_name", "STRING"),
    bigquery.SchemaField("object_type", "STRING"),
    bigquery.SchemaField("owner", "STRING"),
    bigquery.SchemaField("launch_date", "DATE"),
    bigquery.SchemaField("decay_date", "DATE"),
    bigquery.SchemaField("period_min", "FLOAT64"),
    bigquery.SchemaField("apogee_km", "FLOAT64"),
    bigquery.SchemaField("perigee_km", "FLOAT64"),
    bigquery.SchemaField("inclination_deg", "FLOAT64"),
    bigquery.SchemaField("orbit_center", "STRING"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
]

ELEMENT_SETS_SCHEMA = [
    bigquery.SchemaField("norad_cat_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("epoch", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("mean_motion", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("eccentricity", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("inclination_deg", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("ra_of_asc_node_deg", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("arg_of_pericenter_deg", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("mean_anomaly_deg", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("bstar", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("derived_period_min", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("derived_apogee_km", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("derived_perigee_km", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("orbit_class", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("delta_period_min", "FLOAT64"),
    bigquery.SchemaField("delta_apogee_km", "FLOAT64"),
    bigquery.SchemaField("delta_perigee_km", "FLOAT64"),
    bigquery.SchemaField("flagged", "BOOL"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
]


def table_id(name: str) -> str:
    """Full BigQuery ID for a table in this project's dataset."""
    project = os.environ["GCP_PROJECT"]
    dataset = os.environ["BQ_DATASET"]
    return f"{project}.{dataset}.{name}"


def create_tables(client: bigquery.Client) -> None:
    """Create both tables if they don't exist. Safe to re-run."""
    objects_table_id = table_id("objects")
    table = bigquery.Table(objects_table_id, schema=OBJECTS_SCHEMA)
    client.create_table(table, exists_ok=True)

    element_sets_table_id = table_id("element_sets")
    table = bigquery.Table(element_sets_table_id, schema=ELEMENT_SETS_SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(field="loaded_at")
    client.create_table(table, exists_ok=True)


def satcat_to_row(record: SatcatRecord, loaded_at: datetime) -> dict:
    """One SatcatRecord -> one dict keyed by the objects table's column names."""
    data = record.model_dump(mode="json")
    return {
        "norad_cat_id": data["norad_cat_id"],
        "object_id": data["object_id"],
        "object_name": data["object_name"],
        "object_type": data["object_type"],
        "owner": data["owner"],
        "launch_date": data["launch_date"],
        "decay_date": data["decay_date"],
        "period_min": data["period"],
        "apogee_km": data["apogee"],
        "perigee_km": data["perigee"],
        "inclination_deg": data["inclination"],
        "orbit_center": data["orbit_center"],
        "loaded_at": loaded_at.isoformat(),
    }


def load_objects(client: bigquery.Client, rows: list[dict]) -> None:
    """Replace the objects table with these rows."""
    job_config = bigquery.LoadJobConfig(
        schema=OBJECTS_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_json(rows, table_id("objects"), job_config=job_config)
    job.result()
