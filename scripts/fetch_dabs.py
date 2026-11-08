#!/usr/bin/env python3
"""Fetch today's and tomorrow's DABS PDFs from Skybriefing and parse them into GeoJSON.

Usage: python fetch_dabs.py [data_dir [api_dir]]

Requires: poppler-utils (pdftotext), same as dabs_parser.py. No Python dependencies.
Fails loudly (exit code 1) if a fetch or parse fails, so a scheduled job never
silently leaves stale data published. The one exception is a 404, which just means
that day's DABS isn't published yet: that stops the script cleanly (exit code 0),
keeping whatever was already written for earlier sources. Exact area outlines from
shv_airspaces are best-effort, read from the copy kept in data/shv/ (refreshed daily by
update-airspaces.yml) and fetched once if there is none: if that fails, circles are kept and a warning is printed. The same applies when the
downloaded PDF just says the DABS "is not available yet".

Each successfully parsed PDF is also kept as data/pdf/dabs-<date>-v<version>-<generated>.pdf.
The timestamp is the PDF's own "generated" time (UTC, marked "-UTC" in the name), not
the time it was downloaded, so fetching the same version again just overwrites the same
file instead of adding a new one. A PDF that fails to parse is kept for debugging as
data/pdf/failed/<label>-<download time>-UTC.pdf, since it has no parsed header to name
it after.

Each parsed day is also written in the versioned format for apps (api_v1.py), and the
index of the days still to come is rewritten, even when a day isn't published yet.
"""
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import api_v1
from dabs_parser import NotAvailableError, parse
from shv_airspaces import (
    KEPT_FILE,
    apply_airspace_polygons,
    dabs_airspaces,
    fetch_airspaces,
    load_airspaces,
    save_airspaces,
)

SOURCES = {
    "today": "https://www.skybriefing.com/o/dabs?today",
    "tomorrow": "https://www.skybriefing.com/o/dabs?tomorrow",
}


def fetch(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "easydabs/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())


def pdf_name(fc) -> str:
    props = fc["properties"]
    generated = datetime.fromisoformat(props["generated_utc"]).astimezone(timezone.utc).strftime("%Y%m%d_%H%M-UTC")
    return f"dabs-{props['dabs_date']}-v{props['version']}-{generated}.pdf"


def airspaces_for(data_dir: Path):
    """Exact outlines from the copy the daily job keeps; fetched and kept once if there is none yet.

    They are an enhancement: if this BETA API is down, the covering circles stay rather than
    the whole run failing."""
    kept = load_airspaces(data_dir / KEPT_FILE)
    if kept is not None:
        return kept
    try:
        fetched = dabs_airspaces(fetch_airspaces())
    except Exception as e:
        print(f"WARNING: airspace outlines unavailable, using circles: {e}", file=sys.stderr)
        return None
    save_airspaces(data_dir / KEPT_FILE, fetched)
    return fetched


def main():
    repo = Path(__file__).parent.parent
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "data"
    api_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else repo / "api" / "v1"
    pdf_dir = data_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    airspaces = airspaces_for(data_dir)

    not_published = False
    with tempfile.TemporaryDirectory() as tmp:
        for label, url in SOURCES.items():
            pdf_path = Path(tmp) / f"{label}.pdf"
            try:
                fetch(url, pdf_path)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"No document for {label} available")
                    not_published = True
                    break
                print(f"FETCH ERROR ({label}): {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"FETCH ERROR ({label}): {e}", file=sys.stderr)
                sys.exit(1)
            try:
                fc = parse(str(pdf_path))
            except NotAvailableError:
                print(f"No document for {label} available (not published yet)")
                not_published = True
                break
            except Exception as e:
                failed_dir = pdf_dir / "failed"
                failed_dir.mkdir(exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S-UTC")
                failed_path = failed_dir / f"{label}-{stamp}.pdf"
                shutil.copyfile(pdf_path, failed_path)
                print(f"PARSE ERROR ({label}): {e} (PDF kept as {failed_path})", file=sys.stderr)
                sys.exit(1)
            if airspaces:
                apply_airspace_polygons(fc, airspaces)
            out_path = data_dir / f"dabs-{fc['properties']['dabs_date']}.geojson"
            out_path.write_text(json.dumps(fc, indent=2, ensure_ascii=False))
            api_v1.write_day(api_dir, fc)
            shutil.copyfile(pdf_path, pdf_dir / pdf_name(fc))
            print(
                f"OK: {label} -> {out_path.name}, {len(fc['features'])} areas, "
                f"v{fc['properties']['version']}",
                file=sys.stderr,
            )

    api_v1.write_index(api_dir, api_v1.utc_today())
    if not_published:
        sys.exit(0)


if __name__ == "__main__":
    main()
