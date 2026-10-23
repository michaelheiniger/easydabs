import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from dabs_parser import (  # noqa: E402
    circle,
    dms,
    limit,
    parse_header,
    parse_text,
    polygon_from_text,
    radius_candidates,
    utc_iso,
)


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class DmsTests(unittest.TestCase):
    def test_northeast(self):
        # Same coordinate string as the real LSR18 area in data/dabs-2026-10-03.geojson,
        # so the expected result is cross-checked against committed, known-good output.
        lat, lon = dms("472612N0070011E")
        self.assertAlmostEqual(lat, 47.436667, places=5)
        self.assertAlmostEqual(lon, 7.003056, places=5)

    def test_southwest_is_negative(self):
        lat, lon = dms("123456S0123456W")
        self.assertLess(lat, 0)
        self.assertLess(lon, 0)


class LimitTests(unittest.TestCase):
    def test_gnd(self):
        self.assertEqual(limit("GND"), {"raw": "GND", "meters": 0, "feet": 0, "flight_level": None, "gnd": True})

    def test_flight_level(self):
        out = limit("FL100")
        self.assertEqual(out["flight_level"], 100)
        self.assertEqual(out["feet"], 10000)
        self.assertEqual(out["meters"], round(10000 * 0.3048))
        self.assertFalse(out["gnd"])

    def test_meters_feet(self):
        out = limit("1350m / 4500ft")
        self.assertEqual(out["meters"], 1350)
        self.assertEqual(out["feet"], 4500)
        self.assertFalse(out["gnd"])

    def test_unrecognized_raw_is_preserved_but_unparsed(self):
        out = limit("???")
        self.assertEqual(out["raw"], "???")
        self.assertIsNone(out["meters"])
        self.assertIsNone(out["feet"])
        self.assertFalse(out["gnd"])


class RadiusCandidatesTests(unittest.TestCase):
    def test_table_only(self):
        cands = radius_candidates("3.8", "2.1", "no radius mentioned here")
        self.assertEqual(cands, {"table_km": 3800})

    def test_text_mentions_are_added_with_correct_units(self):
        text = "RADIUS 1.7KM (470305N0082006E RADIUS 1.0NM)"
        cands = radius_candidates("1.8", "1.0", text)
        self.assertEqual(cands["table_km"], 1800)
        self.assertEqual(cands["text_0_km"], 1700)
        self.assertEqual(cands["text_1_nm"], 1852)


class CircleTests(unittest.TestCase):
    def test_ring_is_closed_with_64_plus_1_points(self):
        ring = circle(47.0, 8.0, 1000)
        self.assertEqual(len(ring), 65)
        self.assertEqual(ring[0], ring[-1])

    def test_points_are_approximately_at_the_requested_radius(self):
        lat, lon, radius_m = 47.0, 8.0, 2000
        ring = circle(lat, lon, radius_m)
        for lon_pt, lat_pt in ring[:-1:16]:  # sample a few points around the ring
            d = haversine_m(lat, lon, lat_pt, lon_pt)
            self.assertAlmostEqual(d, radius_m, delta=radius_m * 0.01)


class PolygonFromTextTests(unittest.TestCase):
    def test_extracts_closed_ring_from_area_clause(self):
        text = (
            "SOME NOTAM TEXT. AREA: 463000N0063000E 463000N0064000E "
            "462000N0064000E 462000N0063000E 463000N0063000E"
        )
        ring = polygon_from_text(text)
        self.assertEqual(len(ring), 5)
        self.assertEqual(ring[0], ring[-1])

    def test_returns_none_without_area_clause(self):
        self.assertIsNone(polygon_from_text("NO POLYGON HERE, JUST RADIUS 1.0KM."))

    def test_returns_none_with_too_few_points(self):
        text = "AREA: 463000N0063000E 462000N0063000E 463000N0063000E"
        self.assertIsNone(polygon_from_text(text))


class ParseHeaderTests(unittest.TestCase):
    def test_parses_date_version_and_generated_timestamp(self):
        text = "DABS Date: 2026 OCT 03\nVersion 3 - generated: 03.10.2026 10:45 UTC\n"
        date, version, generated = parse_header(text)
        self.assertEqual(date, "2026-10-03")
        self.assertEqual(version, 3)
        self.assertEqual(generated, "2026-10-03T10:45:00+00:00")

    def test_raises_when_header_missing(self):
        with self.assertRaises(ValueError):
            parse_header("nothing useful here")


class UtcIsoTests(unittest.TestCase):
    def test_builds_utc_timestamp(self):
        self.assertEqual(utc_iso("2026-10-03", "0530"), "2026-10-03T05:30:00+00:00")


# pdftotext -layout output is whitespace-column-aligned, but the parser's regexes
# only rely on whitespace runs (\s+), not fixed column positions, so plain
# single-space-separated fixtures below exercise the same code paths.
FIXTURE_TEXT = """\
DABS Date: 2026 OCT 03
Version 3 - generated: 03.10.2026 10:45 UTC

Firings / AIP-Areas / Warnings:
LSR18 0530 - 2359 GND 1350m / 4500ft 472612N0070011E 3.8KM / 2.1NM R-AREA LSR18 BURE ACT DUE TO MIL UAV ACT.
{notam_cont}W2610/26
W2514/26 0700 - 1730 GND 2100m / 6900ft 463525N0062402E 1.5KM / 0.8NM INTENSE GLD ACT.
{area_cont}AREA: 463000N0063000E 463000N0064000E 462000N0064000E 462000N0063000E 463000N0063000E

Activities not shown on the DABS Chart Side:
W9999/26 0800 - 1200 FL050 FL100 460000N0070000E 1.0KM / 0.5NM TEST NOT ON CHART AREA.
""".format(notam_cont=" " * 5, area_cont=" " * 45)


class ParseTextTests(unittest.TestCase):
    def setUp(self):
        self.fc = parse_text(FIXTURE_TEXT)

    def test_top_level_properties(self):
        self.assertEqual(self.fc["type"], "FeatureCollection")
        self.assertEqual(
            self.fc["properties"],
            {"dabs_date": "2026-10-03", "version": 3, "generated_utc": "2026-10-03T10:45:00+00:00"},
        )

    def test_feature_count(self):
        self.assertEqual(len(self.fc["features"]), 3)

    def _by_id(self, area_id):
        return next(f for f in self.fc["features"] if f["properties"]["id"] == area_id)

    def test_named_area_with_notam_continuation_line(self):
        props = self._by_id("LSR18")["properties"]
        self.assertEqual(props["notam"], "W2610/26")
        self.assertTrue(props["on_chart"])
        self.assertEqual(props["geometry_source"], "circle")
        self.assertEqual(props["radius_m"], 3800)
        self.assertEqual(props["center"], {"lat": 47.436667, "lon": 7.003056})
        self.assertTrue(props["lower"]["gnd"])
        self.assertEqual(props["upper"]["meters"], 1350)

    def test_area_with_explicit_polygon_from_item_e(self):
        props = self._by_id("W2514/26")["properties"]
        self.assertEqual(props["notam"], "W2514/26")  # id itself is the NOTAM number; no separate name
        self.assertEqual(props["geometry_source"], "polygon")
        ring = self._by_id("W2514/26")["geometry"]["coordinates"][0]
        self.assertEqual(len(ring), 5)
        self.assertEqual(ring[0], ring[-1])

    def test_not_on_chart_area_and_flight_levels(self):
        props = self._by_id("W9999/26")["properties"]
        self.assertFalse(props["on_chart"])
        self.assertEqual(props["lower"]["flight_level"], 50)
        self.assertEqual(props["lower"]["feet"], 5000)
        self.assertEqual(props["upper"]["flight_level"], 100)
        self.assertEqual(props["upper"]["feet"], 10000)

    def test_validity_window(self):
        props = self._by_id("LSR18")["properties"]
        self.assertEqual(props["valid_from_utc"], "2026-10-03T05:30:00+00:00")
        self.assertEqual(props["valid_to_utc"], "2026-10-03T23:59:00+00:00")


# Verbatim (column-aligned) excerpts from the real DABS 2026-10-14 v4 PDF, since the
# cases below depend on pdftotext's actual indentation, not just whitespace runs.
LAYOUT_TEXT = """\
                                  KOSIF                                           DABS Date: 2026 OCT 14
                                                                                  Version 4 - generated: 14.10.2026 13:45 UTC
Firings / AIP-Areas / Warnings:
 LSR39B        1200 - 1400        2750m / 9000ft   FL130             465352N 0082513E   10.1KM / 5.5NM       R-AREA LSR39B BRISEN ACT. LOWER LIMIT 9000FT AMSL OR 2000FT GND WHICHEVER IS
 W2752/26                                                                                                    HIGHER.

 W2590/26      0000 - 2359        GND              2300m / 7650ft    462225N 0070018E   1.1KM / 0.6NM        HIGHLINE OBST ERECTED 3.9KM NNW HLP LEYSIN.
                                                                                                             LGT. MAX ALT UP TO 186M AGL.


Page 2                                                                                                                                                                                     a MICAMS product
                              KOSIF                                               DABS Date: 2026 OCT 14                                            E-mail:        kosif@skyguide.ch
                                                                                   Version 4 - generated: 14.10.2026 13:45 UTC

Activities not shown on the DABS Chart Side:
! W2784/26    1745 - 2145      FL060             FL100              464500N 0080800E     181.5KM / 98.1NM     MIL NGT FLT WITH UNMANNED ACFT WILL TAKE PLACE WI AIRSPACE SWITZERLAND. OTHER           !
                                                                                                              AIRSPACE USERS SHALL CTC TACTICAL OPS CENTER ON +41 58 467 29 10 FOR COOR.

For detailed information regarding the DABS see AIP Switzerland GEN 3.1-5 or VFR GEN 1-0-4.
! New or changed data regarding an earlier version of the DABS.
"""


class ParseLayoutTests(unittest.TestCase):
    def setUp(self):
        self.by_id = {f["properties"]["id"]: f["properties"] for f in parse_text(LAYOUT_TEXT)["features"]}

    def test_feature_count(self):
        self.assertEqual(set(self.by_id), {"LSR39B", "W2590/26", "W2784/26"})

    def test_changed_row_marked_with_exclamation_marks_is_parsed(self):
        props = self.by_id["W2784/26"]
        self.assertFalse(props["on_chart"])
        self.assertEqual(props["lower"]["flight_level"], 60)
        self.assertEqual(
            props["text"],
            "MIL NGT FLT WITH UNMANNED ACFT WILL TAKE PLACE WI AIRSPACE SWITZERLAND. OTHER "
            "AIRSPACE USERS SHALL CTC TACTICAL OPS CENTER ON +41 58 467 29 10 FOR COOR.",
        )

    def test_country_sized_covering_circle_is_unmapped(self):
        self.assertEqual(self.by_id["W2784/26"]["geometry_source"], "unmapped")
        self.assertEqual(self.by_id["W2590/26"]["geometry_source"], "circle")

    def test_notam_line_sharing_a_line_with_item_e_continuation(self):
        props = self.by_id["LSR39B"]
        self.assertEqual(props["notam"], "W2752/26")
        self.assertTrue(props["text"].endswith("WHICHEVER IS HIGHER."))

    def test_next_page_letterhead_is_not_appended_to_last_row(self):
        self.assertEqual(
            self.by_id["W2590/26"]["text"],
            "HIGHLINE OBST ERECTED 3.9KM NNW HLP LEYSIN. LGT. MAX ALT UP TO 186M AGL.",
        )


EMPTY_TEXT = """\
DABS Date: 2026 OCT 24
Version 1 - generated: 23.10.2026 13:22 UTC

Firings / AIP-Areas / Warnings:
Firing-Nr Validity Lower Limit Upper Limit Center Point Covering Radius NOTAM Item E
{pad}There are no planned activities for 24.10.2026

Activities not shown on the DABS Chart Side:
NOTAM-Nr Validity Lower Limit Upper Limit Center Point Covering Radius NOTAM Item E
{pad}There are no planned activities for 24.10.2026
""".format(pad=" " * 86)


class ParseEmptyDayTests(unittest.TestCase):
    def test_day_without_activities_yields_no_features(self):
        fc = parse_text(EMPTY_TEXT)
        self.assertEqual(fc["features"], [])
        self.assertEqual(fc["properties"]["dabs_date"], "2026-10-24")
        self.assertEqual(fc["properties"]["version"], 1)

    def test_one_empty_section_alongside_rows(self):
        text = FIXTURE_TEXT.split("Activities not shown")[0] + (
            "Activities not shown on the DABS Chart Side:\n"
            "There are no planned activities for 03.10.2026\n")
        fc = parse_text(text)
        self.assertEqual(len(fc["features"]), 2)
        self.assertTrue(all(f["properties"]["on_chart"] for f in fc["features"]))

    def test_raises_when_a_section_has_neither_rows_nor_empty_statement(self):
        text = EMPTY_TEXT.replace("There are no planned activities for 24.10.2026", "garbled", 1)
        with self.assertRaises(ValueError):
            parse_text(text)


class ParseTextErrorTests(unittest.TestCase):
    def test_raises_when_no_rows_found(self):
        text = "DABS Date: 2026 OCT 03\nVersion 1 - generated: 03.10.2026 10:45 UTC\n"
        with self.assertRaises(ValueError):
            parse_text(text)

    def test_raises_when_header_missing(self):
        with self.assertRaises(ValueError):
            parse_text("Firings / AIP-Areas / Warnings:\nsome nonsense line\n")


if __name__ == "__main__":
    unittest.main()
