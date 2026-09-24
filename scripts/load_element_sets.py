import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from google.cloud import bigquery

from orbital_catalog.fetch import latest_run_dir
from orbital_catalog.load import load_gp_file, load_satcat_file
from orbital_catalog.reconcile import latest_per_object, reconcile_all
from orbital_catalog.sources import PHASE1_GP_GROUPS, gp_group
from orbital_catalog.warehouse import element_set_to_row, load_element_sets

load_dotenv()


def main() -> int:
    loaded_at = datetime.now(timezone.utc)
    run = latest_run_dir()

    satcat = load_satcat_file(run / "satcat_full.csv")
    gp_records = []
    for group in PHASE1_GP_GROUPS:
        gp_records.extend(load_gp_file(run / gp_group(group).filename))

    pairs = reconcile_all(latest_per_object(gp_records), satcat)
    rows = [element_set_to_row(gp, rec, loaded_at) for gp, rec in pairs]

    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    load_element_sets(client, rows, loaded_at)
    print(f"{len(rows)} rows loaded into partition {loaded_at:%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())