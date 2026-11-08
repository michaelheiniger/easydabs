import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from shv_airspaces import (  # noqa: E402
    apply_airspace_polygons,
    dabs_airspaces,
    index_by_id,
    load_airspaces,
    save_airspaces,
)

RING_A = [[7.0, 46.0], [7.1, 46.0], [7.1, 46.1], [7.0, 46.0]]
RING_B = [[8.0, 46.0], [8.1, 46.0], [8.1, 46.1], [8.0, 46.0]]


def shv(name, ring, dabs=True):
    return {
        "type": "Feature",
        "properties": {"Name": name, "DABS": dabs},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def dabs_feature(area_id, source="circle"):
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "properties": {"id": area_id, "geometry_source": source},
    }


class ApplyTests(unittest.TestCase):
    def apply(self, features, shv_features):
        fc = {"features": features}
        n = apply_airspace_polygons(fc, {"features": shv_features})
        return fc, n

    def test_replaces_circle_matching_first_word_of_name(self):
        fc, n = self.apply([dabs_feature("LSR7")], [shv("LSR7 Hongrin", RING_A)])
        f = fc["features"][0]
        self.assertEqual(n, 1)
        self.assertEqual(f["geometry"], {"type": "Polygon", "coordinates": [RING_A]})
        self.assertEqual(f["properties"]["geometry_source"], "airspace")

    def test_matches_full_name_case_and_space_insensitively(self):
        fc, n = self.apply([dabs_feature("TMA  SION 1")], [shv("TMA Sion 1", RING_A)])
        self.assertEqual(n, 1)

    def test_id_is_not_a_prefix_match(self):
        fc, n = self.apply([dabs_feature("LSR1")], [shv("LSR11 Zuoz", RING_A)])
        self.assertEqual(n, 0)
        self.assertEqual(fc["features"][0]["properties"]["geometry_source"], "circle")

    def test_multiple_polygons_for_one_id_become_multipolygon(self):
        fc, n = self.apply(
            [dabs_feature("LSR6")],
            [shv("LSR6 AXALP NORD", RING_A), shv("LSR6 AXALP SUD", RING_B)],
        )
        self.assertEqual(fc["features"][0]["geometry"]["type"], "MultiPolygon")
        self.assertEqual(fc["features"][0]["geometry"]["coordinates"], [[RING_A], [RING_B]])

    def test_ignores_non_dabs_airspaces(self):
        _, n = self.apply([dabs_feature("LSR7")], [shv("LSR7 Hongrin", RING_A, dabs=False)])
        self.assertEqual(n, 0)

    def test_keeps_text_polygons_and_unmatched_areas(self):
        feats = [dabs_feature("LSR7", source="polygon"), dabs_feature("W1234/26")]
        before = copy.deepcopy(feats)
        _, n = self.apply(feats, [shv("LSR7 Hongrin", RING_A)])
        self.assertEqual(n, 0)
        self.assertEqual(feats, before)

    def test_index_skips_non_polygon_geometry(self):
        f = shv("LSR7 Hongrin", RING_A)
        f["geometry"]["type"] = "Point"
        self.assertEqual(index_by_id({"features": [f]}), {})


class KeepTests(unittest.TestCase):
    def test_keeps_only_the_airspaces_the_dabs_activates(self):
        airspaces = {"features": [shv("LSR7 Hongrin", RING_A), shv("CTR Bern", RING_B, dabs=False)]}
        kept = dabs_airspaces(airspaces)
        self.assertEqual([f["properties"]["Name"] for f in kept["features"]], ["LSR7 Hongrin"])
        self.assertEqual(kept["type"], "FeatureCollection")

    def test_reads_back_what_it_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shv" / "dabs-airspaces.geojson"
            kept = dabs_airspaces({"features": [shv("LSR7 Hongrin", RING_A)]})
            save_airspaces(path, kept)
            self.assertEqual(load_airspaces(path), kept)

    def test_nothing_kept_reads_as_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_airspaces(Path(tmp) / "missing.geojson"))

    def test_an_unreadable_copy_reads_as_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dabs-airspaces.geojson"
            path.write_text('{"features": [')
            self.assertIsNone(load_airspaces(path))


if __name__ == "__main__":
    unittest.main()
