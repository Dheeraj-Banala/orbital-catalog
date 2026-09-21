from pathlib import Path
import csv
from .models import GPRecord, SatcatRecord


def load_gp_file(path: Path) -> list[GPRecord]:
    """Read one gp_*.csv and return one validated record per row."""
    with open(path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        record_list = []
        for row in reader:
            record_list.append(GPRecord.model_validate(row))
    return record_list


def load_satcat_file(path: Path) -> dict[int, SatcatRecord]:
    """Read one satcat_*.csv and return one record keyed by NORAD catalog ID"""
    with open(path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        record_dict = {}
        for row in reader:
            record = SatcatRecord.model_validate(row)
            record_dict[record.norad_cat_id] = record
    return record_dict
