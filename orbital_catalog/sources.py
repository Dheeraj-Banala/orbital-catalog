"""Celestrak source definitions.

Two endpoints matter for this project:

  GP   (general perturbations) -- gp.php     -> orbital element sets, the thing that
       actually describes where an object's orbit is. Served per GROUP.
  SATCAT (satellite catalog)   -- records.php -> the metadata about each object:
       who owns it, when it launched, is it a payload or debris, has it decayed.

They join on NORAD_CAT_ID.

Verified against celestrak.org docs on 2026-07-26:
  https://celestrak.org/NORAD/documentation/gp-data-formats.php
  https://celestrak.org/satcat/satcat-format.php
"""

from dataclasses import dataclass

GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
SATCAT_URL = "https://celestrak.org/satcat/records.php"


@dataclass(frozen=True)
class Source:
    """One thing we pull, one file it lands in."""

    name: str
    url: str
    params: dict[str, str]
    ext: str

    @property
    def filename(self) -> str:
        return f"{self.name}.{self.ext}"


def gp_group(group: str) -> Source:
    """Orbital element sets for one Celestrak group, as CSV."""
    return Source(
        name=f"gp_{group}",
        url=GP_URL,
        params={"GROUP": group, "FORMAT": "csv"},
        ext="csv",
    )


# `starlink` is deliberately absent: it's a subset of `active`, so pulling it would
# re-download the same satellites from a strictly enforced endpoint.
PHASE1_GP_GROUPS = [
    "stations",  # ISS, CSS -- tiny, good smoke test
    "gps-ops",   # ~30 objects, MEO, clean
    "visual",    # ~150 brightest, mixed orbits
    "weather",   # ~70, sun-synchronous LEO
    "geo",       # geostationary belt -- very different orbit shape from the others
    "active",    # ~16.6K active satellites (~11K Starlink) Strictly enforced: one pull per day.
]

# The FULL catalog -- every tracked object, ~31.6K of them: live payloads, dead ones,
# spent rocket bodies, debris.
#
# This is a flat file, NOT the records.php query API. The query API requires a GROUP,
# and the only GROUPs it offers are `active` and `analyst` -- `active` returns ~16.6K
# rows that are 99.99% payloads. Debris and rocket bodies are the interesting half of
# this project ("how much of what's up there is junk?"), so the query API cannot serve
# the headline feature. Verified 2026-07-26.
SATCAT_FULL = Source(
    name="satcat_full",
    url="https://celestrak.org/pub/satcat.csv",
    params={},
    ext="csv",
)


def phase1_sources() -> list[Source]:
    return [gp_group(g) for g in PHASE1_GP_GROUPS] + [SATCAT_FULL]
