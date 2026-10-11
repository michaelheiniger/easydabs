"""Exact airspace outlines from the Swiss hang-gliding/paragliding federation's map API.

The DABS PDF only gives a centre + radius for most permanent areas (R-/D-areas, TMAs),
so dabs_parser draws a covering circle. The SHV/FSVL airspace API publishes the real
polygons for every area flagged ``DABS: true``; apply_airspace_polygons() swaps them in
by area id (e.g. DABS 'LSR7' <-> SHV 'LSR7 Hongrin').

Docs: https://airspace.shv-fsvl.ch/doc/beta/geojson (BETA API - hence the fail-soft
callers, see fetch_dabs.py).
"""
import json
import re
import urllib.request

URL = "https://airspace.shv-fsvl.ch/api/beta/geojson/airspaces"


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
