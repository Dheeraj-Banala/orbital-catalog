import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbital_catalog.load import load_gp_file
from orbital_catalog.fetch import RAW_DIR


def main() -> int:
    path = RAW_DIR / "2026-07-26" / "gp_stations.csv"
    records = load_gp_file(path)
    print(f"{len(records)} records loaded")

    for record in records:
        if record.norad_cat_id == 25544:
            print(repr(record))
            return 0
    print("not found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

