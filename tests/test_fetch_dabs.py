import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_dabs  # noqa: E402

FC_TODAY = {
    "type": "FeatureCollection",
    "properties": {"dabs_date": "2026-10-03", "version": 1, "generated_utc": "2026-10-03T10:45:00+00:00"},
    "features": [],
}
FC_TOMORROW = {
    "type": "FeatureCollection",
    "properties": {"dabs_date": "2026-10-04", "version": 1, "generated_utc": "2026-10-03T13:25:00+00:00"},
    "features": [],
}


class MainTests(unittest.TestCase):
    def test_writes_one_geojson_file_per_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_dabs, "fetch"), \
                 patch.object(fetch_dabs, "parse", side_effect=[FC_TODAY, FC_TOMORROW]):
                sys.argv = ["fetch_dabs.py", tmp]
                fetch_dabs.main()

            today_path = Path(tmp) / "dabs-2026-10-03.geojson"
            tomorrow_path = Path(tmp) / "dabs-2026-10-04.geojson"
            self.assertTrue(today_path.exists())
            self.assertTrue(tomorrow_path.exists())
            self.assertEqual(json.loads(today_path.read_text()), FC_TODAY)
            self.assertEqual(json.loads(tomorrow_path.read_text()), FC_TOMORROW)

    def test_creates_data_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "data"
            with patch.object(fetch_dabs, "fetch"), \
                 patch.object(fetch_dabs, "parse", side_effect=[FC_TODAY, FC_TOMORROW]):
                sys.argv = ["fetch_dabs.py", str(target)]
                fetch_dabs.main()
            self.assertTrue(target.is_dir())

    def test_exits_nonzero_when_fetch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_dabs, "fetch", side_effect=OSError("network down")):
                sys.argv = ["fetch_dabs.py", tmp]
                with self.assertRaises(SystemExit) as ctx:
                    fetch_dabs.main()
                self.assertEqual(ctx.exception.code, 1)

    def test_exits_nonzero_when_parse_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_dabs, "fetch"), \
                 patch.object(fetch_dabs, "parse", side_effect=ValueError("bad layout")):
                sys.argv = ["fetch_dabs.py", tmp]
                with self.assertRaises(SystemExit) as ctx:
                    fetch_dabs.main()
                self.assertEqual(ctx.exception.code, 1)


class FetchTests(unittest.TestCase):
    def test_fetch_writes_response_bytes_with_user_agent_header(self):
        seen_requests = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return b"%PDF-1.4 fake content"

        def fake_urlopen(req, timeout=None):
            seen_requests.append(req)
            return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.pdf"
            with patch.object(fetch_dabs.urllib.request, "urlopen", side_effect=fake_urlopen):
                fetch_dabs.fetch("https://example.test/dabs", dest)

            self.assertEqual(dest.read_bytes(), b"%PDF-1.4 fake content")
            self.assertEqual(len(seen_requests), 1)
            self.assertEqual(seen_requests[0].get_header("User-agent"), "easydabs/1.0")


if __name__ == "__main__":
    unittest.main()
