import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from google.cloud import bigquery

from orbital_catalog.load import load_satcat_file
from orbital_catalog.fetch import latest_run_dir
from orbital_catalog.warehouse import satcat_to_row, load_objects

load_dotenv()


def main() -> int:
    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    loaded_at = datetime.now(timezone.utc)
    satcat = load_satcat_file(latest_run_dir() / "satcat_full.csv")
    rows = []
    for record in satcat.values():
        rows.append(satcat_to_row(record, loaded_at))

    load_objects(client, rows)
    print(f"{len(rows)} rows loaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())