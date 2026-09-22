import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbital_catalog.reconcile import reconcile
from orbital_catalog.load import load_gp_file, load_satcat_file
from orbital_catalog.fetch import RAW_DIR
from orbital_catalog.sources import PHASE1_GP_GROUPS, gp_group


def main() -> int:
    run = RAW_DIR / "2026-07-26"
    satcat = load_satcat_file(run / "satcat_full.csv")

    gp_records = []
    for group in PHASE1_GP_GROUPS:
        gp_records.extend(load_gp_file(run / gp_group(group).filename))
    print(f"{len(gp_records)} GP records from {len(PHASE1_GP_GROUPS)} files")

    best = {}
    for record in gp_records:
        current = best.get(record.norad_cat_id)
        if current is None or record.epoch > current.epoch:
            best[record.norad_cat_id] = record
    deduped = list(best.values())

    misses = 0
    results = []
    for gp in deduped:
        satcat_match = satcat.get(gp.norad_cat_id)
        if satcat_match is None:
            misses += 1
            continue
        results.append(reconcile(gp, satcat_match))

    print(f"{len(deduped)} after dedup")
    print(f"{misses} with no SATCAT match")
    print(f"{len(results)} reconciled")

    for result in results:
        if result.norad_cat_id == 25544:
            print(result)
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())