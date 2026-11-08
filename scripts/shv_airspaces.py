"""Exact airspace outlines from the Swiss hang-gliding/paragliding federation's map API.

The DABS PDF only gives a centre + radius for most permanent areas (R-/D-areas, TMAs),
so dabs_parser draws a covering circle. The SHV/FSVL airspace API publishes the real
polygons for every area flagged ``DABS: true``; apply_airspace_polygons() swaps them in
by area id (e.g. DABS 'LSR7' <-> SHV 'LSR7 Hongrin').

Docs: https://airspace.shv-fsvl.ch/doc/beta/geojson (BETA API - hence the fail-soft
callers, see fetch_dabs.py).

The outlines change about once a year, so they are not fetched on every hourly run:
run on its own (python shv_airspaces.py [data_dir]), this script keeps the airspaces
the DABS activates in data/shv/, and update-airspaces.yml runs it once a day, early in
the morning. fetch_dabs.py reads that copy.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://airspace.shv-fsvl.ch/api/beta/geojson/airspaces"
# Relative to the data directory.
KEPT_FILE = Path("shv") / "dabs-airspaces.geojson"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().upper()


def fetch_airspaces(url: str = URL) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "easydabs/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def index_by_id(airspaces: dict) -> dict:
    """Map normalised DABS id -> list of polygon rings-lists, from DABS-flagged airspaces.

    Keyed by the first word of the name ('LSR7 Hongrin' -> 'LSR7') and by the full name
    ('TMA Sion 1'). One id may map to several polygons (e.g. 'LSR6 AXALP NORD' / 'SUD')."""
    index = {}
    for f in airspaces.get("features", []):
        if not f.get("properties", {}).get("DABS"):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "Polygon":
            continue
        name = _norm(f["properties"].get("Name", ""))
        if not name:
            continue
        for key in {name, name.split(" ")[0]}:
            polys = index.setdefault(key, [])
            if geom["coordinates"] not in polys:
                polys.append(geom["coordinates"])
    return index


def apply_airspace_polygons(fc: dict, airspaces: dict) -> int:
    """Replace circle geometry with the exact outline where one is known.
    Returns the number of features replaced. Areas with an explicit NOTAM-text
    polygon, or with no match, are left untouched."""
    index = index_by_id(airspaces)
    replaced = 0
    for feat in fc["features"]:
        props = feat["properties"]
        if props["geometry_source"] != "circle":
            continue
        polys = index.get(_norm(props["id"]))
        if not polys:
            continue
        if len(polys) == 1:
            feat["geometry"] = {"type": "Polygon", "coordinates": polys[0]}
        else:
            feat["geometry"] = {"type": "MultiPolygon", "coordinates": polys}
        props["geometry_source"] = "airspace"
        replaced += 1
    return replaced


def dabs_airspaces(airspaces: dict) -> dict:
    """Only the airspaces the DABS activates: all apply_airspace_polygons() uses."""
    return {
        "type": "FeatureCollection",
        "features": [f for f in airspaces.get("features", []) if f.get("properties", {}).get("DABS")],
    }


def save_airspaces(path: Path, airspaces: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(airspaces, ensure_ascii=False, separators=(",", ":")))


def load_airspaces(path: Path):
    """The kept airspaces, or None when there is no readable copy."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "data"
    try:
        airspaces = dabs_airspaces(fetch_airspaces())
    except Exception as e:  # fail loudly for CI; the copy kept so far stays in use
        print(f"FETCH ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    save_airspaces(data_dir / KEPT_FILE, airspaces)
    print(f"OK: {len(airspaces['features'])} DABS airspaces kept", file=sys.stderr)


if __name__ == "__main__":
    main()
