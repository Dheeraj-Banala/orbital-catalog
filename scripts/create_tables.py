import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from google.cloud import bigquery
from orbital_catalog.warehouse import create_tables

load_dotenv()


def main() -> int:
    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    create_tables(client)
    print("Tables ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())