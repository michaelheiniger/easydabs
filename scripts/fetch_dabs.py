#!/usr/bin/env python3
"""Fetch today's and tomorrow's DABS PDFs from Skybriefing and parse them into GeoJSON.

Usage: python fetch_dabs.py [data_dir]

Requires: poppler-utils (pdftotext), same as dabs_parser.py. No Python dependencies.
Fails loudly (exit code 1) if a fetch or parse fails, so a scheduled job never
silently leaves stale data published. The one exception is a 404, which just means
that day's DABS isn't published yet: that stops the script cleanly (exit code 0),
keeping whatever was already written for earlier sources.
"""
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dabs_parser import parse

SOURCES = {
    "today": "https://www.skybriefing.com/o/dabs?today",
    "tomorrow": "https://www.skybriefing.com/o/dabs?tomorrow",
}


def fetch(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "easydabs/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        for label, url in SOURCES.items():
            pdf_path = Path(tmp) / f"{label}.pdf"
            try:
                fetch(url, pdf_path)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"No document for {label} available")
                    sys.exit(0)
                print(f"FETCH ERROR ({label}): {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"FETCH ERROR ({label}): {e}", file=sys.stderr)
                sys.exit(1)
            try:
                fc = parse(str(pdf_path))
            except Exception as e:
                print(f"PARSE ERROR ({label}): {e}", file=sys.stderr)
                sys.exit(1)
            out_path = data_dir / f"dabs-{fc['properties']['dabs_date']}.geojson"
            out_path.write_text(json.dumps(fc, indent=2, ensure_ascii=False))
            print(
                f"OK: {label} -> {out_path.name}, {len(fc['features'])} areas, "
                f"v{fc['properties']['version']}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
