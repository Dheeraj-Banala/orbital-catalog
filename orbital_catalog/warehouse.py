import os

from google.cloud import bigquery

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
