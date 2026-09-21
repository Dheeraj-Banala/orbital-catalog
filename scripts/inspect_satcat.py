import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbital_catalog.load import load_satcat_file
from orbital_catalog.fetch import RAW_DIR


def main() -> int:
    path = RAW_DIR / "2026-07-26" / "satcat_full.csv"
    satcat = load_satcat_file(path)
    print(f"{len(satcat)} records loaded")

    if 25544 in satcat:
        print(repr(satcat[25544]))
        return 0
    print("not found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

