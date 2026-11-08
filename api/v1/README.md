# EasyDABS API, version 1

Machine-readable DABS (Daily Airspace Bulletin Switzerland) for apps, served as static
files next to the website:

| File | Contents |
| --- | --- |
| `index.json` | The days from today (UTC, like the DABS day) onwards that have a published DABS. Schema: [`index.schema.json`](index.schema.json) |
| `dabs-<date>.json` | One DABS day, as a GeoJSON FeatureCollection. Schema: [`dabs-day.schema.json`](dabs-day.schema.json) |

The files are rewritten by the hourly update job (`scripts/fetch_dabs.py`, mapping in
`scripts/api_v1.py`) and checked against the schemas in CI.

> **Disclaimer:** situational awareness only, with no guarantee of accuracy or
> completeness. The official DABS on [Skybriefing](https://www.skybriefing.com/o/dabs)
> is the only authoritative source. An app showing this data must say so and link to it.

## Reading it

1. Fetch `index.json`. A day not listed is not published yet: Skybriefing publishes
   tomorrow's DABS during the afternoon.
2. Fetch the day's `path`, relative to the index. Its `version` and `generated_utc` say
   which edition of the DABS it is, as printed on the official PDF.
3. Use conditional requests (`If-None-Match`): the files only change when the DABS does.

## A day

Top-level `properties`:

| Field | Meaning |
| --- | --- |
| `schema_version` | `1.<minor>` of this format |
| `dabs_date` | The DABS day (a UTC day, see Validity), `YYYY-MM-DD` |
| `version` | The DABS edition of that day; Skybriefing publishes a new one when an activity changes |
| `generated_utc` | When Skybriefing generated that edition |

Each feature is one area. Its `geometry` is a `Polygon` or `MultiPolygon` in WGS 84
`[longitude, latitude]`, or `null` when `shape` is `unmapped`. Ring orientation is not
guaranteed. Its `properties`:

| Field | Meaning |
| --- | --- |
| `id` | The area's designator (e.g. `LSR7`), or the NOTAM number when the DABS gives no other name |
| `notam` | The NOTAM number, or `null` |
| `on_chart` | Whether the DABS lists it on its chart side (a publication detail, not a severity) |
| `validity` | See below |
| `lower`, `upper` | Vertical limits, see below |
| `shape` | Where the outline comes from: `polygon` (coordinates in the NOTAM text), `airspace` (exact outline from the [SHV/FSVL airspace API](https://airspace.shv-fsvl.ch/)), `circle` (centre and radius from the DABS table) or `unmapped` (a circle covering the whole country, meaning "somewhere in Switzerland": list it, don't draw it) |
| `center`, `radius_m` | The centre and radius the DABS table gives, for every shape. For `circle` they define the outline, using the largest radius the DABS states |
| `text` | The NOTAM's original text (Item E), in English as ICAO requires. Never translate it |

### Validity

`from_utc` and `to_utc` are the times the DABS prints, which are UTC: convert them to
local time like any other instant. A DABS day appears to be the UTC day: activities
running all day are printed 0000–2359, and night activities are cut at 2359 UTC.
`from_start_of_day` and `to_end_of_day` are `true` when an activity starts at 0000 or
ends at 2359, i.e. where the bulletin may cut it at its day boundary: it can go on in
the previous or next day's DABS, and 2359 then stands for the end of the day.

### Vertical limits

`kind` says which fields are present. `raw` is always the text the DABS prints.

| `kind` | Fields |
| --- | --- |
| `ground` | none |
| `flight_level` | `flight_level` (hundreds of feet, standard pressure). Not converted: convert in the app if needed |
| `altitude` | `meters` and `feet`, both as printed (they are not exact conversions of each other) |
| `unknown` | none: show `raw` |

## Versioning

- **Minor** (`1.0` → `1.1`): fields or `kind`/`shape` values are only added. Readers must
  ignore fields they don't know, and treat an unknown `kind` like `unknown` and an
  unknown `shape` like `unmapped`.
- **Major**: anything else (a field removed, renamed or changing meaning) goes to a new
  `api/v2/`, published next to `v1` while apps move over.
