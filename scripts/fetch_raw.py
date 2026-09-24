"""Phase 1 entrypoint: prove the source works and land raw data.

    python scripts/fetch_raw.py
    python scripts/fetch_raw.py --force     # re-download even if today's files exist

--force exists for when a file landed truncated. Do not use it to iterate on parsing;
that is what the landing zone is for.
"""

import argparse
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from orbital_catalog.fetch import SourceUnavailable, fetch_all, run_dir
from orbital_catalog.sources import phase1_sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download cached files")
    args = parser.parse_args()

    sources = phase1_sources()
    print(f"Landing {len(sources)} sources into {run_dir()}")

    try:
        landed = asyncio.run(fetch_all(sources, force=args.force))
    except SourceUnavailable as exc:
        print(f"\nSTOPPED: {exc}", file=sys.stderr)
        return 1

    total = sum(p.stat().st_size for p in landed)
    print(f"\n{len(landed)} files, {total:,} bytes total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
