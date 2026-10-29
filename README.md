# EasyDABS

**Live app: https://michaelheiniger.github.io/easydabs/web/index.html**

EasyDABS shows Switzerland's daily airspace bulletin, the
[DABS](https://www.skybriefing.com/o/dabs) (Daily Airspace Bulletin Switzerland), on an
interactive, zoomable map, so you don't have to read the low-resolution static map
embedded in the official PDF. It covers restricted and danger areas, military activity,
air displays, obstacles and similar items.

> **Disclaimer:** EasyDABS is for situational awareness only. It comes with no guarantee
> of accuracy or completeness. The official DABS publication on
> [Skybriefing](https://www.skybriefing.com/o/dabs) is the only authoritative source.
> Always check it before you fly.

## Features

- Today's and tomorrow's DABS, one tab each.
- Every area drawn on a detailed swisstopo basemap. Exact outlines are used where they
  are known; otherwise the area is shown as a circle.
- A list of all areas next to the map. Click an area, or select it with the keyboard,
  to zoom to it and open its details: validity times, vertical limits and the original
  NOTAM text.
- All times shown in Swiss local time.
- Interface in English, French, German and Italian. NOTAM text stays in its original
  English, as ICAO requires; it is never machine-translated.
- Works on phones and tablets.
- A built-in "Report an error" form for flagging a wrong or missing area.

## How it works

1. A GitHub Actions workflow (`.github/workflows/update-dabs.yml`) runs every hour. It
   downloads today's and tomorrow's DABS PDFs from Skybriefing.
2. `scripts/dabs_parser.py` extracts the text with `pdftotext` and parses each entry
   into GeoJSON. `scripts/shv_airspaces.py` swaps circles for exact polygons from the
   [SHV/FSVL airspace API](https://airspace.shv-fsvl.ch/) where it has them.
3. The result is committed to `data/dabs-<date>.geojson`, but only when the content has
   actually changed. Source PDFs are archived under `data/pdf/`.
4. The static frontend in `web/` (plain HTML/JS/CSS with [Leaflet](https://leafletjs.com/),
   no build step) loads the GeoJSON and renders it. It is deployed to GitHub Pages by
   `.github/workflows/deploy-pages.yml`.

If a download or parse fails, the update job fails loudly instead of quietly leaving
stale data online.

## Repository layout

| Path | Contents |
| --- | --- |
| `scripts/` | Fetching and parsing scripts (Python standard library only) |
| `data/` | Generated GeoJSON per day, plus the archived source PDFs |
| `web/` | The frontend: `index.html`, `app.js`, `i18n.js`, `style.css` |
| `tests/` | Python unit tests for the parser and fetch scripts |
| `tests-ui/` | Playwright tests for the frontend |
| `.github/workflows/` | Tests, hourly data update, Pages deployment |

## Running locally

Requirements: Python 3, plus `poppler-utils` (for `pdftotext`) if you want to fetch and
parse real PDFs. Node.js is only needed for the UI tests.

Serve the frontend from the repository root, so that both `/web/` and `/data/` resolve:

```bash
python3 -m http.server 8731
```

Then open http://localhost:8731/web/index.html.

Fetch and parse the current DABS yourself:

```bash
python3 scripts/fetch_dabs.py
```

## Tests

Python tests (parser and fetch logic; they need neither `pdftotext` nor network access):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

UI tests (one-time setup first):

```bash
npm install
```

```bash
npx playwright install chromium
```

```bash
npx playwright test
```

Both suites run on every pull request and on every push to `main`.

## Contributing and feedback

Use the "Report an error" button in the app, or open an issue or pull request on this
repository. [`CLAUDE.md`](CLAUDE.md) has detailed notes on the architecture and on
pitfalls that have already been hit, especially around map zoom behaviour. Read it before
changing the map code.
