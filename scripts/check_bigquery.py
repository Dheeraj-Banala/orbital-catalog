import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()


def main() -> int:
    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    datasets = [d.dataset_id for d in client.list_datasets()]
    print(f"Connected to {client.project}. Datasets: {datasets}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())