from pathlib import Path
import csv
from .models import GPRecord


def load_gp_file(path: Path) -> list[GPRecord]:
    """Read one gp_*.csv and return one validated record per row."""
    with open(path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        record_list = []
        for row in reader:
            record_list.append(GPRecord.model_validate(row))
    return record_list