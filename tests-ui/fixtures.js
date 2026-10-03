// Shared GeoJSON fixture for UI tests. Kept deliberately independent of the
// real wall-clock date: tests intercept every data/dabs-*.geojson request and
// serve this fixture regardless of which date file was actually asked for,
// so the suite behaves identically whether it runs today or next year (the
// repo's committed data/*.geojson samples are dated and would otherwise go
// stale and 404 against the "today"/"tomorrow" tabs).

const FIXTURE_FC = {
  type: "FeatureCollection",
  properties: { dabs_date: "2026-01-01", version: 1, generated_utc: "2026-01-01T10:00:00+00:00" },
  features: [
    {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [[[7.0, 47.0], [7.01, 47.0], [7.01, 47.01], [7.0, 47.01], [7.0, 47.0]]],
      },
      properties: {
        id: "TEST1",
        notam: "W1234/26",
        on_chart: true,
        valid_from_utc: "2026-01-01T05:00:00+00:00",
        valid_to_utc: "2026-01-01T10:00:00+00:00",
        lower: { raw: "GND", meters: 0, feet: 0, flight_level: null, gnd: true },
        upper: { raw: "1000m / 3281ft", meters: 1000, feet: 3281, flight_level: null, gnd: false },
        center: { lat: 47.005, lon: 7.005 },
        radius_m: 500,
        radius_candidates_m: { table_km: 500 },
        geometry_source: "circle",
        text: "TEST AREA ONE ON CHART.",
      },
    },
    {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [[[8.0, 46.5], [8.01, 46.5], [8.01, 46.51], [8.0, 46.51], [8.0, 46.5]]],
      },
      properties: {
        id: "W5678/26",
        notam: "W5678/26",
        on_chart: false,
        valid_from_utc: "2026-01-01T12:00:00+00:00",
        valid_to_utc: "2026-01-01T14:00:00+00:00",
        lower: { raw: "GND", meters: 0, feet: 0, flight_level: null, gnd: true },
        upper: { raw: "FL100", meters: 3048, feet: 10000, flight_level: 100, gnd: false },
        center: { lat: 46.505, lon: 8.005 },
        radius_m: 800,
        radius_candidates_m: { table_km: 800 },
        geometry_source: "circle",
        text: "TEST AREA TWO NOT ON CHART.",
      },
    },
  ],
};

const EMPTY_FC = {
  type: "FeatureCollection",
  properties: { dabs_date: "2026-01-01", version: 1, generated_utc: "2026-01-01T10:00:00+00:00" },
  features: [],
};

async function mockDabsData(page, fc = FIXTURE_FC) {
  await page.route("**/data/dabs-*.geojson", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(fc) })
  );
}

module.exports = { FIXTURE_FC, EMPTY_FC, mockDabsData };
