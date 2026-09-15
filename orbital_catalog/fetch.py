"""Pull raw Celestrak data to disk. No parsing, no transforming -- land it and stop.

The landing zone is the point. Every later phase (parsing, deriving orbital params,
loading BigQuery) replays from these files instead of re-hitting the network, which
is both how a real pipeline is built and how we stay inside Celestrak's usage policy
while iterating.

Policy rules encoded here (celestrak.org/usage-policy.php):
  - Download once per update, not once per run. Same-day file already on disk -> skip.
  - Any non-200 means stop, immediately, no retry loop. Celestrak asks machine clients
    to back off on 301/403/404/50x rather than hammer.
  - Identify yourself in the User-Agent.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import httpx

from .sources import Source

def user_agent() -> str:
    """Celestrak asks automated clients to identify themselves with a contact address.

    Read from the environment rather than hardcoded, so a real address isn't published
    in a public repo. Set CELESTRAK_CONTACT in .env (loaded by the entrypoint) or in
    your shell. Read at call time, not import time, so load order can't silently
    produce an anonymous User-Agent.
    """
    contact = os.environ.get("CELESTRAK_CONTACT")
    if not contact:
        raise RuntimeError(
            "CELESTRAK_CONTACT is not set. Celestrak asks automated clients to be "
            "reachable -- put an address you monitor in .env before running."
        )
    return f"orbital-catalog/0.1 (personal project; {contact})"

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"

TIMEOUT = httpx.Timeout(30.0)


class SourceUnavailable(Exception):
    """Celestrak answered with something other than 200. Stop, don't retry."""


def run_dir(run_date: dt.date | None = None) -> Path:
    """One directory per UTC day. Re-running the same day reuses it."""
    run_date = run_date or dt.datetime.now(dt.timezone.utc).date()
    return RAW_DIR / run_date.isoformat()


def fetch_one(
    client: httpx.Client,
    source: Source,
    dest_dir: Path,
    force: bool = False,
) -> tuple[Path, bool]:
    """Land one source. Returns (path, downloaded) -- downloaded=False means cache hit."""
    dest = dest_dir / source.filename

    if dest.exists() and not force:
        return dest, False

    response = client.get(source.url, params=source.params)

    if response.status_code != 200:
        raise SourceUnavailable(
            f"{source.name}: HTTP {response.status_code} from {response.url}. "
            "Celestrak's policy is to stop on any non-200 -- not to retry. "
            "A 403 here usually means this data has not updated since the last pull."
        )

    # Celestrak returns 200 with an error string in the body for some bad queries,
    # so a plausibility check beats trusting the status code alone.
    body = response.text
    if len(body) < 200 or "Invalid query" in body:
        raise SourceUnavailable(
            f"{source.name}: HTTP 200 but the body looks wrong "
            f"({len(body)} bytes): {body[:200]!r}"
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    return dest, True


def fetch_all(sources: list[Source], force: bool = False) -> list[Path]:
    """Land every source, sequentially.

    Sequential on purpose: concurrency is Phase 3, and doing it here would mean
    writing it before there is anything to measure it against. httpx (not requests)
    so that phase is a Client -> AsyncClient swap rather than a rewrite.
    """
    dest_dir = run_dir()
    landed: list[Path] = []

    with httpx.Client(
        headers={"User-Agent": user_agent()},
        timeout=TIMEOUT,
        follow_redirects=False,  # policy: a 301 is a signal to fix the URL, not to chase it
    ) as client:
        for source in sources:
            path, downloaded = fetch_one(client, source, dest_dir, force=force)
            size = path.stat().st_size
            status = "downloaded" if downloaded else "cached"
            print(f"  {source.name:<24} {status:<11} {size:>9,} bytes")
            landed.append(path)

    return landed
