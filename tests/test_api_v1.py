import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import api_v1  # noqa: E402
from dabs_parser import circle, parse_text  # noqa: E402
from test_dabs_parser import FIXTURE_TEXT, LAYOUT_TEXT  # noqa: E402

API_DIR = Path(__file__).resolve().parent.parent / "api" / "v1"
DAY_SCHEMA = json.loads((API_DIR / "dabs-day.schema.json").read_text())
INDEX_SCHEMA = json.loads((API_DIR / "index.schema.json").read_text())


def validate(instance, schema):
    jsonschema.validate(instance, schema, cls=jsonschema.Draft202012Validator)


def parsed_limit(raw, meters=None, feet=None, flight_level=None, gnd=False):
    return {"raw": raw, "meters": meters, "feet": feet, "flight_level": flight_level, "gnd": gnd}


GLIDER_FLYING_RARON = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [circle(46.304444, 7.821667, 1667)]},
    "properties": {
        "id": "W2996/26",
        "notam": "W2996/26",
        "on_chart": False,
        "valid_from_utc": "2026-11-08T09:00:00+00:00",
        "valid_to_utc": "2026-11-08T16:00:00+00:00",
        "lower": parsed_limit("GND", meters=0, feet=0, gnd=True),
        "upper": parsed_limit("2000m / 6500ft", meters=2000, feet=6500),
        "center": {"lat": 46.304444, "lon": 7.821667},
        "radius_m": 1667,
        "radius_candidates_m": {"table_km": 1500, "text_0_km": 1500, "text_1_nm": 1667},
        "geometry_source": "circle",
        "text": "GLD FLYING WILL TAKE PLACE AT LSTA AD, RADIUS 1.5KM (461816N0074918E RADIUS 0.9NM).",
    },
}


def parsed_area(**overrides):
    return {**GLIDER_FLYING_RARON, "properties": {**GLIDER_FLYING_RARON["properties"], **overrides}}


def parsed_day(dabs_date="2026-11-08", version=1, features=()):
    return {
        "type": "FeatureCollection",
        "properties": {"dabs_date": dabs_date, "version": version, "generated_utc": "2026-11-07T14:31:00+00:00"},
        "features": list(features),
    }


class VerticalLimitTests(unittest.TestCase):
    def test_ground_keeps_only_its_kind_and_raw_text(self):
        # given
        parsed = parsed_limit("GND", meters=0, feet=0, gnd=True)
        # when
        limit = api_v1.vertical_limit(parsed)
        # then
        self.assertEqual(limit, {"kind": "ground", "raw": "GND"})

    def test_flight_level_is_not_converted_to_metres_or_feet(self):
        # given
        parsed = parsed_limit("FL195", meters=5944, feet=19500, flight_level=195)
        # when
        limit = api_v1.vertical_limit(parsed)
        # then
        self.assertEqual(limit, {"kind": "flight_level", "raw": "FL195", "flight_level": 195})

    def test_altitude_keeps_both_published_units(self):
        # given
        parsed = parsed_limit("2000m / 6500ft", meters=2000, feet=6500)
        # when
        limit = api_v1.vertical_limit(parsed)
        # then
        self.assertEqual(limit, {"kind": "altitude", "raw": "2000m / 6500ft", "meters": 2000, "feet": 6500})

    def test_unrecognised_limit_keeps_the_raw_text_for_display(self):
        # given
        parsed = parsed_limit("SFC")
        # when
        limit = api_v1.vertical_limit(parsed)
        # then
        self.assertEqual(limit, {"kind": "unknown", "raw": "SFC"})


class ValidityTests(unittest.TestCase):
    def test_times_within_the_day_are_real_instants(self):
        # given
        props = parsed_area()["properties"]
        # when
        validity = api_v1.validity(props)
        # then
        self.assertEqual(validity, {
            "from_utc": "2026-11-08T09:00:00Z",
            "to_utc": "2026-11-08T16:00:00Z",
            "from_start_of_day": False,
            "to_end_of_day": False,
        })

    def test_dabs_day_boundaries_are_flagged(self):
        # given
        props = parsed_area(
            valid_from_utc="2026-11-08T00:00:00+00:00",
            valid_to_utc="2026-11-08T23:59:00+00:00",
        )["properties"]
        # when
        validity = api_v1.validity(props)
        # then
        self.assertTrue(validity["from_start_of_day"])
        self.assertTrue(validity["to_end_of_day"])
        self.assertEqual(validity["to_utc"], "2026-11-08T23:59:00Z")


class FeatureTests(unittest.TestCase):
    def test_circle_keeps_its_outline_centre_and_radius(self):
        # given
        parsed = parsed_area()
        # when
        area = api_v1.feature(parsed)
        # then
        self.assertEqual(area["geometry"], parsed["geometry"])
        self.assertEqual(area["properties"]["shape"], "circle")
        self.assertEqual(area["properties"]["center"], {"lat": 46.304444, "lon": 7.821667})
        self.assertEqual(area["properties"]["radius_m"], 1667)

    def test_parser_debug_fields_are_not_published(self):
        # given
        parsed = parsed_area()
        # when
        area = api_v1.feature(parsed)
        # then
        self.assertNotIn("radius_candidates_m", area["properties"])
        self.assertNotIn("geometry_source", area["properties"])
        self.assertNotIn("valid_from_utc", area["properties"])

    def test_country_sized_area_has_no_geometry(self):
        # given
        parsed = parsed_area(id="W2784/26", notam="W2784/26", geometry_source="unmapped", radius_m=181500)
        # when
        area = api_v1.feature(parsed)
        # then
        self.assertIsNone(area["geometry"])
        self.assertEqual(area["properties"]["shape"], "unmapped")

    def test_exact_airspace_outline_is_kept_as_multipolygon(self):
        # given
        ring = circle(46.53, 8.05, 2000)
        parsed = {
            **parsed_area(id="LSR6", notam="W2900/26", geometry_source="airspace"),
            "geometry": {"type": "MultiPolygon", "coordinates": [[ring], [ring]]},
        }
        # when
        area = api_v1.feature(parsed)
        # then
        self.assertEqual(area["geometry"]["type"], "MultiPolygon")
        self.assertEqual(area["properties"]["shape"], "airspace")


class DayTests(unittest.TestCase):
    def test_header_carries_the_schema_version_and_utc_publication_time(self):
        # given
        parsed = parsed_day(features=[parsed_area()])
        # when
        day = api_v1.day(parsed)
        # then
        self.assertEqual(day["properties"], {
            "schema_version": api_v1.SCHEMA_VERSION,
            "dabs_date": "2026-11-08",
            "version": 1,
            "generated_utc": "2026-11-07T14:31:00Z",
        })
        self.assertEqual(len(day["features"]), 1)

    def test_written_file_is_compact_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            # given
            parsed = parsed_day(features=[parsed_area()])
            # when
            path = api_v1.write_day(Path(tmp), parsed)
            # then
            self.assertEqual(path.name, "dabs-2026-11-08.json")
            self.assertNotIn("\n", path.read_text())
            self.assertNotIn(", ", path.read_text().split('"text"')[0])

    def test_parsed_fixtures_map_to_valid_days(self):
        for text in (FIXTURE_TEXT, LAYOUT_TEXT):
            with self.subTest(fixture=text[:40]):
                # given
                parsed = parse_text(text)
                # when
                day = api_v1.day(parsed)
                # then
                validate(day, DAY_SCHEMA)


class IndexTests(unittest.TestCase):
    def test_lists_the_days_from_today_onwards_oldest_first(self):
        # given
        days = [api_v1.day(parsed_day(d)) for d in ("2026-11-09", "2026-11-07", "2026-11-08")]
        # when
        index = api_v1.index(days, today=date(2026, 11, 8))
        # then
        self.assertEqual(index["days"], [
            {"dabs_date": "2026-11-08", "version": 1, "generated_utc": "2026-11-07T14:31:00Z",
             "path": "dabs-2026-11-08.json"},
            {"dabs_date": "2026-11-09", "version": 1, "generated_utc": "2026-11-07T14:31:00Z",
             "path": "dabs-2026-11-09.json"},
        ])
        validate(index, INDEX_SCHEMA)

    def test_no_day_published_yet_gives_an_empty_list(self):
        # given
        days = [api_v1.day(parsed_day("2026-11-07"))]
        # when
        index = api_v1.index(days, today=date(2026, 11, 8))
        # then
        self.assertEqual(index, {"schema_version": api_v1.SCHEMA_VERSION, "days": []})

    def test_written_index_reads_only_day_files_not_the_schemas(self):
        with tempfile.TemporaryDirectory() as tmp:
            # given
            api = Path(tmp)
            (api / "dabs-day.schema.json").write_text(json.dumps(DAY_SCHEMA))
            api_v1.write_day(api, parsed_day("2026-11-08"))
            # when
            path = api_v1.write_index(api, today=date(2026, 11, 8))
            # then
            index = json.loads(path.read_text())
            self.assertEqual([d["dabs_date"] for d in index["days"]], ["2026-11-08"])


class PublishedFilesTests(unittest.TestCase):
    """What is committed is what apps download: it must match the published schemas."""

    def test_schemas_are_valid_json_schemas(self):
        jsonschema.Draft202012Validator.check_schema(DAY_SCHEMA)
        jsonschema.Draft202012Validator.check_schema(INDEX_SCHEMA)

    def test_every_published_day_matches_the_schema(self):
        for path in sorted(API_DIR.glob(api_v1.DAY_FILE_GLOB)):
            with self.subTest(path=path.name):
                validate(json.loads(path.read_text()), DAY_SCHEMA)

    def test_published_index_matches_the_schema(self):
        validate(json.loads((API_DIR / api_v1.INDEX_FILE).read_text()), INDEX_SCHEMA)


if __name__ == "__main__":
    unittest.main()
