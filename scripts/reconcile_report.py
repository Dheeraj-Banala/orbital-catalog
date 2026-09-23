import sys
import statistics
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orbital_catalog.reconcile import latest_per_object, reconcile_all
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

    deduped = latest_per_object(gp_records)

    pairs = reconcile_all(deduped, satcat)
    results = [rec for _, rec in pairs]
    misses = len(deduped) - len(pairs)

    print(f"{len(deduped)} after dedup")
    print(f"{misses} with no SATCAT match")
    print(f"{len(results)} reconciled")

    for result in results:
        if result.norad_cat_id == 25544:
            print(result)
            break

    groups = defaultdict(list)
    for result in results:
        groups[result.orbit_class].append(result)

    print(f"{'class':<6} {'n':>5} {'median_km':>10} {'worst_km':>10} {'flagged':>8}")

    for orbit_class, group in sorted(groups.items()):
        flagged_count = sum(1 for r in group if r.flagged)
        gaps = [abs(r.delta_perigee_km) for r in group if r.delta_perigee_km is not None]
        if not gaps:
            print(f"{orbit_class}: n/a")
            continue
        median = statistics.median(gaps)
        worst = max(gaps)
        print(f"{orbit_class:<6} {len(group):>5} {median:>10.2f} {worst:>10.2f} {flagged_count:>8}")

    with_gap = [r for r in results if r.delta_perigee_km is not None]
    worst_first = sorted(with_gap, key=lambda r: abs(r.delta_perigee_km), reverse=True)

    print()
    print(f"{'name':<28} {'class':<6} {'epoch':<16} {'derived':>9} {'satcat':>9} {'delta':>8}")
    for r in worst_first[:10]:
        print(
            f"{r.name[:28]:<28} {r.orbit_class:<6} {r.epoch:%Y-%m-%d %H:%M} "
            f"{r.derived_perigee_km:>9.1f} {r.satcat_perigee_km:>9.1f} {r.delta_perigee_km:>+8.2f}"
        )

    print()
    print("Flagged:")
    for r in results:
        if r.flagged:
            print(f"  {r.name} ({r.orbit_class})")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())