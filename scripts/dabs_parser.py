#!/usr/bin/env python3
"""Parse a Skyguide DABS PDF (text side) into GeoJSON.

Usage: python dabs_parser.py dabs.pdf [out.geojson]

Requires: poppler-utils (pdftotext). No Python dependencies.
Fails loudly (exit code 1) if the layout doesn't look as expected, so a
scheduled job never publishes silently-wrong data.
"""
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone

MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}

COORD = r"\d{6}[NS]\s?\d{7}[EW]"
ROW_RE = re.compile(
    rf"^\s*(?P<id>\S+)\s+(?P<val>\d{{4}} - \d{{4}})\s+(?P<lower>\S+(?: / \S+)?)\s+"
    rf"(?P<upper>\S+(?: / \S+)?)\s+(?P<center>{COORD})\s+"
    rf"(?P<km>[\d.]+)KM / (?P<nm>[\d.]+)NM\s+(?P<text>.*)$"
)
NOTAM_RE = re.compile(r"^[A-Z]\d{4}/\d{2}$")
SECTION_RE = re.compile(r"^\s*(Firings / AIP-Areas / Warnings|Activities not shown on the DABS Chart Side):")


def dms(coord: str):
    """472612N 0070011E -> (lat, lon) in decimal degrees."""
    m = re.match(r"(\d{2})(\d{2})(\d{2})([NS])\s?(\d{3})(\d{2})(\d{2})([EW])", coord)
    lat = int(m[1]) + int(m[2]) / 60 + int(m[3]) / 3600
    lon = int(m[5]) + int(m[6]) / 60 + int(m[7]) / 3600
    return (-lat if m[4] == "S" else lat), (-lon if m[8] == "W" else lon)


def limit(raw: str):
    raw = raw.strip()
    out = {"raw": raw, "meters": None, "feet": None, "flight_level": None, "gnd": False}
    if raw == "GND":
        out.update(gnd=True, meters=0, feet=0)
    elif raw.startswith("FL"):
        fl = int(raw[2:])
        out.update(flight_level=fl, feet=fl * 100, meters=round(fl * 100 * 0.3048))
    else:
        m = re.match(r"(\d+)m / (\d+)ft", raw)
        if m:
            out.update(meters=int(m[1]), feet=int(m[2]))
    return out


def radius_candidates(km: str, nm: str, text: str):
    """Radius values (metres) stated for an area: the table's KM value and any
    'RADIUS x KM' / 'RADIUS x NM' in the NOTAM text. The table's NM column is
    deliberately ignored: it is rounded up to 0.1 NM and would inflate the radius."""
    cands = {"table_km": float(km) * 1000}
    for i, (val, unit) in enumerate(re.findall(r"RADIUS\s+([\d.]+)\s*(KM|NM)", text)):
        cands[f"text_{i}_{unit.lower()}"] = float(val) * (1000 if unit == "KM" else 1852)
    return {k: round(v) for k, v in cands.items()}


def circle(lat, lon, radius_m, n=64):
    """Approximate geodesic circle as a closed GeoJSON ring [lon, lat]."""
    R = 6371008.8
    d = radius_m / R
    la, lo = math.radians(lat), math.radians(lon)
    ring = []
    for i in range(n):
        b = 2 * math.pi * i / n
        la2 = math.asin(math.sin(la) * math.cos(d) + math.cos(la) * math.sin(d) * math.cos(b))
        lo2 = lo + math.atan2(math.sin(b) * math.sin(d) * math.cos(la),
                              math.cos(d) - math.sin(la) * math.sin(la2))
        ring.append([round(math.degrees(lo2), 6), round(math.degrees(la2), 6)])
    ring.append(ring[0])
    return ring


def polygon_from_text(text: str):
    """Use an explicit polygon from Item E if present ('WI AREA: c1 c2 ... c1')."""
    m = re.search(rf"AREA:\s*((?:{COORD}\s*){{4,}})", text)
    if not m:
        return None
    pts = [dms(c) for c in re.findall(COORD, m[1])]
    ring = [[round(lon, 6), round(lat, 6)] for lat, lon in pts]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring if len(ring) >= 4 else None


def parse_header(text: str):
    d = re.search(r"DABS Date:\s*(\d{4}) ([A-Z]{3}) (\d{1,2})", text)
    v = re.search(r"Version (\d+) - generated: (\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}) UTC", text)
    if not d or not v:
        raise ValueError("DABS header not found")
    date = f"{int(d[1]):04d}-{MONTHS[d[2]]:02d}-{int(d[3]):02d}"
    gen = datetime(int(v[4]), int(v[3]), int(v[2]), int(v[5]), int(v[6]), tzinfo=timezone.utc)
    return date, int(v[1]), gen.isoformat()


def utc_iso(date: str, hhmm: str, end=False):
    h, m = int(hhmm[:2]), int(hhmm[2:])
    dt = datetime.fromisoformat(date).replace(hour=h, minute=m, tzinfo=timezone.utc)
    return dt.isoformat()


def parse(pdf_path: str):
    text = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                          capture_output=True, text=True, check=True).stdout
    return parse_text(text)


def parse_text(text: str):
    date, version, generated = parse_header(text)

    rows, section = [], None
    for line in text.splitlines():
        s = SECTION_RE.match(line)
        if s:
            section = "chart" if s[1].startswith("Firings") else "not_on_chart"
            continue
        if section is None:
            continue
        m = ROW_RE.match(line)
        if m:
            rows.append({"section": section, "m": m, "extra_ids": [], "text": [m["text"].strip()]})
            continue
        if not rows or rows[-1]["section"] != section or not line.strip():
            continue
        stripped = line.strip()
        if NOTAM_RE.match(stripped) and len(line) - len(line.lstrip()) < 6:
            rows[-1]["extra_ids"].append(stripped)          # NOTAM-Nr on its own line
        elif len(line) - len(line.lstrip()) > 40:            # Item E continuation
            rows[-1]["text"].append(stripped)

    if not rows:
        raise ValueError("No airspace rows found - layout changed?")

    features = []
    for r in rows:
        m = r["m"]
        first = m["id"]
        ids = [first] + r["extra_ids"]
        notams = [i for i in ids if NOTAM_RE.match(i)]
        names = [i for i in ids if not NOTAM_RE.match(i)]
        item_e = " ".join(r["text"])
        lat, lon = dms(m["center"])
        cands = radius_candidates(m["km"], m["nm"], item_e)
        radius_m = max(cands.values())   # conservative: largest stated radius
        v0, v1 = m["val"].split(" - ")
        poly = polygon_from_text(item_e)
        geom_kind = "polygon" if poly else "circle"
        ring = poly or circle(lat, lon, radius_m)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "id": names[0] if names else notams[0],
                "notam": notams[0] if notams else None,
                "on_chart": r["section"] == "chart",
                "valid_from_utc": utc_iso(date, v0),
                "valid_to_utc": utc_iso(date, v1),
                "lower": limit(m["lower"]),
                "upper": limit(m["upper"]),
                "center": {"lat": round(lat, 6), "lon": round(lon, 6)},
                "radius_m": radius_m,
                "radius_candidates_m": cands,
                "geometry_source": geom_kind,   # 'polygon' = from NOTAM text, 'circle' = covering circle
                "text": item_e,
            },
        })

    return {
        "type": "FeatureCollection",
        "properties": {"dabs_date": date, "version": version, "generated_utc": generated},
        "features": features,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        fc = parse(sys.argv[1])
    except Exception as e:  # fail loudly for CI
        print(f"PARSE ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    out = json.dumps(fc, indent=2, ensure_ascii=False)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(out)
    else:
        print(out)
    print(f"OK: {len(fc['features'])} areas, DABS {fc['properties']['dabs_date']} "
          f"v{fc['properties']['version']}", file=sys.stderr)
