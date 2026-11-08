#!/usr/bin/env python3
"""The versioned format for apps (api/v1), mapped from the parser's GeoJSON.

Usage: python api_v1.py [data_dir [api_dir]]
Rebuilds api/v1 from every data/dabs-<date>.geojson, e.g. after a minor version adds a
field. fetch_dabs.py writes the same files on every run.

The parser's own output (data/*.geojson) belongs to the website and may change freely.
This format is a contract with apps: api/v1/README.md describes it and how it evolves,
and the JSON Schemas next to it are checked in CI.
"""
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"
# Where the bulletin cuts an activity at its (UTC) day: it may go on in the previous or
# next day's DABS. The times themselves are real UTC instants.
START_OF_DAY = "00:00"
END_OF_DAY = "23:59"
# Dated names only: the schemas live in the same directory.
DAY_FILE_GLOB = "dabs-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"
INDEX_FILE = "index.json"


def utc(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def vertical_limit(parsed: dict) -> dict:
    """Only the values DABS prints: a flight level is not converted to metres, since
    published metric and imperial limits are not exact conversions of each other."""
    raw = parsed["raw"]
    if parsed["gnd"]:
        return {"kind": "ground", "raw": raw}
    if parsed["flight_level"] is not None:
        return {"kind": "flight_level", "raw": raw, "flight_level": parsed["flight_level"]}
    if parsed["meters"] is not None:
        return {"kind": "altitude", "raw": raw, "meters": parsed["meters"], "feet": parsed["feet"]}
    return {"kind": "unknown", "raw": raw}


def validity(props: dict) -> dict:
    start, end = props["valid_from_utc"], props["valid_to_utc"]
    return {
        "from_utc": utc(start),
        "to_utc": utc(end),
        "from_start_of_day": datetime.fromisoformat(start).strftime("%H:%M") == START_OF_DAY,
        "to_end_of_day": datetime.fromisoformat(end).strftime("%H:%M") == END_OF_DAY,
    }


def feature(parsed: dict) -> dict:
    props = parsed["properties"]
    shape = props["geometry_source"]
    return {
        "type": "Feature",
        # A covering circle around the whole country says nothing about where: listed, not drawn.
        "geometry": None if shape == "unmapped" else parsed["geometry"],
        "properties": {
            "id": props["id"],
            "notam": props["notam"],
            "on_chart": props["on_chart"],
            "validity": validity(props),
            "lower": vertical_limit(props["lower"]),
            "upper": vertical_limit(props["upper"]),
            "shape": shape,
            "center": props["center"],
            "radius_m": props["radius_m"],
            "text": props["text"],
        },
    }


def day(parsed_fc: dict) -> dict:
    props = parsed_fc["properties"]
    return {
        "type": "FeatureCollection",
        "properties": {
            "schema_version": SCHEMA_VERSION,
            "dabs_date": props["dabs_date"],
            "version": props["version"],
            "generated_utc": utc(props["generated_utc"]),
        },
        "features": [feature(f) for f in parsed_fc["features"]],
    }


def index(days: list[dict], today: date) -> dict:
    """The days from today onwards, oldest first: what an app can still show."""
    upcoming = sorted(
        (d["properties"] for d in days if date.fromisoformat(d["properties"]["dabs_date"]) >= today),
        key=lambda p: p["dabs_date"],
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "days": [
            {
                "dabs_date": p["dabs_date"],
                "version": p["version"],
                "generated_utc": p["generated_utc"],
                "path": day_file_name(p["dabs_date"]),
            }
            for p in upcoming
        ],
    }


def day_file_name(dabs_date: str) -> str:
    return f"dabs-{dabs_date}.json"


def dumps(obj: dict) -> str:
    # Compact: apps download this over mobile networks.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def write_day(api_dir: Path, parsed_fc: dict) -> Path:
    api_dir.mkdir(parents=True, exist_ok=True)
    v1 = day(parsed_fc)
    path = api_dir / day_file_name(v1["properties"]["dabs_date"])
    path.write_text(dumps(v1))
    return path


def write_index(api_dir: Path, today: date) -> Path:
    api_dir.mkdir(parents=True, exist_ok=True)
    days = [json.loads(p.read_text()) for p in api_dir.glob(DAY_FILE_GLOB)]
    path = api_dir / INDEX_FILE
    path.write_text(dumps(index(days, today)))
    return path


def utc_today() -> date:
    """A DABS day is a UTC day: until it ends, its activities may still be running."""
    return datetime.now(timezone.utc).date()


def main():
    repo = Path(__file__).parent.parent
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "data"
    api_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else repo / "api" / "v1"
    sources = sorted(data_dir.glob("dabs-*.geojson"))
    for source in sources:
        write_day(api_dir, json.loads(source.read_text()))
    write_index(api_dir, utc_today())
    print(f"OK: {len(sources)} days written to {api_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
