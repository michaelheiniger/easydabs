# EasyDABS

Shows Switzerland's daily DABS airspace bulletin (restricted/danger areas, military activity,
air displays, obstacles) on an interactive, high-detail map, instead of the low-resolution
static map embedded in the official PDF. Live at https://michaelheiniger.github.io/easydabs/.

## Architecture

```
scripts/dabs_parser.py   Parses a DABS PDF (via pdftotext -layout) into GeoJSON.
                          parse(pdf_path) is a thin wrapper around parse_text(text) -
                          parse_text is what's actually unit tested, so tests need
                          neither poppler-utils nor a real PDF.
scripts/fetch_dabs.py    Downloads today's + tomorrow's PDFs from skybriefing.com,
                          runs them through dabs_parser, writes data/dabs-<date>.geojson.
                          Fails loudly (exit 1) on any error - never publish stale data
                          silently.
data/*.geojson           Output of fetch_dabs.py. Filename date comes from the PDF's own
                          header (dabs_date), not wall-clock - see parse_header().
web/                     Static frontend: index.html, app.js, i18n.js, style.css.
                          No build step, no framework, no bundler. Leaflet loaded from
                          unpkg. Deployed as-is.
index.html (repo root)   Redirects to web/index.html, so the Pages root URL works.
tests/                   Python unittest suite for the parser/fetch scripts.
tests-ui/                Playwright suite for the frontend (see "UI tests" below).
.github/workflows/
  tests.yml               Python + UI tests, on every PR and push to main.
  update-dabs.yml          Hourly cron: runs fetch_dabs.py, commits data/*.geojson to
                            main only if content actually changed (no commit spam).
  deploy-pages.yml         On push to main: stages the site into a temp dir, stamps the
                            commit SHA onto web/*.{css,js} URLs there, deploys via
                            actions/deploy-pages. See "Cache-busting" below for why.
```

## Running things locally

```bash
# Python tests (parser/fetch logic)
python -m unittest discover -s tests -p "test_*.py" -v

# UI tests (frontend behavior) - first time only:
npm install
npx playwright install chromium
# every time:
npx playwright test
npx playwright test --ui   # interactive/debug mode

# Serve the frontend locally
python3 -m http.server 8731   # from repo root, so /web/ and /data/ both resolve
# open http://localhost:8731/web/index.html
```

**Local-server caching gotcha:** `python -m http.server` sends no cache headers, but
Chrome still caches `app.js`/`style.css` aggressively across reloads. If an edit doesn't
seem to take effect, hard-reload (Ctrl+Shift+R / Cmd+Shift+R) before assuming the bug is
real. This bit us in production too - see "Cache-busting" below.

## Pitfalls already hit (read before touching map/zoom code)

**Leaflet animated zoom can get permanently stuck - never animate.** `flyTo`,
`flyToBounds`, and `setView(..., {animate: true})` all proved unreliable: Leaflet sets an
internal `map._animatingZoom = true` flag when starting a CSS-transition-based zoom, and
only clears it when the transition's `transitionend` DOM event fires. In headless Chrome,
backgrounded/unfocused tabs, and apparently some ordinary conditions too, that event can
simply never fire - which leaves `_animatingZoom` stuck `true` **forever**, silently
no-opping *every subsequent* zoom change for the rest of the page's life, including
unrelated, already-non-animated calls elsewhere (Leaflet won't start a new view change
while it thinks one is still in flight). This was the actual root cause behind a
"zoom doesn't behave properly" bug report that took multiple rounds to pin down. The fix:
every `setView`/`fitBounds` call in `app.js` passes `animate: false`. If you add a new one,
do the same - do not reach for `flyTo` for a "nicer" transition.

**`ResizeObserver` on `#map` is required, not optional.** Leaflet caches the map
container's pixel size at load and never re-measures it on its own. The legend,
disclaimer, and area-list panel are all collapsible (`<details>`), and collapsing/
expanding any of them changes `#map`'s actual size - without a resize hook, Leaflet keeps
panning/zooming against stale dimensions, causing visible drift. `app.js` sets up
`new ResizeObserver(() => map.invalidateSize()).observe(#map)` once at startup; if you add
another element whose toggling can resize `#map`, you don't need to do anything extra -
this is already generic.

**Swisstopo tiles don't exist outside Switzerland.** The default basemap
(`wmts10.geo.admin.ch`) only covers Swiss territory; tiles requested for neighboring
countries 400. This is invisible at normal zoom levels but turns into large blank/grey
patches if the map is ever zoomed out past roughly zoom 6-7 (confirmed via direct tile
HTTP checks, not just visual guessing). Don't lower `minZoom` or the area-select zoom
target without checking tile coverage at that level first.

## Cache-busting / deployment

GitHub Pages serves everything through a fixed CDN with a non-configurable
`Cache-Control: max-age=600` - there is no `_headers` file support like Netlify/Cloudflare
Pages, so response headers can't be tuned. A browser that fetched `app.js`/`style.css`
just before a deploy could run that stale JS/CSS against a newer `index.html` for up to
10 minutes (this happened once in production - map didn't render in Firefox until a hard
refresh).

Fix: Pages is deployed via **GitHub Actions** (`deploy-pages.yml`), not classic
"deploy from branch". That workflow stages the repo into a temp `_site/` dir and
sed-rewrites `style.css`/`app.js`/`i18n.js` references in the *staged copy* to
`style.css?v=<short-sha>` etc. - the tracked source files in `web/index.html` stay
unversioned; only the deployed copy gets the query string. A fresh `index.html` therefore
always points at a uniquely-named asset URL, so the CDN's cache window can never serve a
mismatched JS/CSS pair. `app.js` reads its own version back out of
`document.currentScript.src` (see `APP_VERSION`) and shows it via the Leaflet attribution
control - don't add a separate version file, it'd just be another thing to keep in sync.

**Required one-time repo setting:** Settings → Pages → Source must be "GitHub Actions"
(not "Deploy from a branch"), or this workflow's deploys won't go live.

## i18n

`web/i18n.js` holds one `TRANSLATIONS` object keyed by `en`/`fr`/`de`/`it`, plus
`t(key, vars)`, `setLang()`, `detectLang()` (browser language, falls back to `en`,
persisted in `localStorage`). When adding a new UI string, add the key to **all four**
language blocks - nothing enforces this automatically, and a missing key silently falls
back to the English string via `t()`'s lookup chain.

**NOTAM text itself is never translated**, by design: ICAO mandates NOTAMs be issued in
English, and a machine translation of safety-critical airspace text would be actively
dangerous. Every popup labels the raw text as original/English so this reads as
intentional. Don't "fix" this.

## Mobile

Two breakpoints in `style.css`: `760px` (stacks the area list below the map instead of
beside it) and `480px` (tightens header/disclaimer spacing, enlarges touch targets).
`IS_TOUCH` in `app.js` (`'ontouchstart' in window || navigator.maxTouchPoints > 0`) swaps
the area-list hint text from the keyboard shortcut to "tap to select" - there's no
physical keyboard on a phone. The area-list panel's default open/collapsed state is also
decided by viewport width at load time (`matchMedia("(max-width: 760px)")`), set **once**
and deliberately not re-applied on resize, so it never fights a user's manual toggle.

## Collapsible panels (legend, disclaimer, area list)

All three use native `<details>/<summary>` - no JS needed for the expand/collapse
mechanic itself, which is why there's no corresponding `onclick` handler to find. When
collapsed, make sure CSS doesn't leave an element forced to its *open* size: the area-list
panel specifically needs `width: auto; align-self: flex-start` when closed, or it reserves
its full column width/height and leaves an empty void instead of giving the space to the
map (this was a real bug, not hypothetical - check before adding another collapsible flex
child).

## UI tests (`tests-ui/`)

Playwright, config in `playwright.config.js` (spins up `python3 -m http.server 8731`
itself via `webServer`). `tests-ui/fixtures.js` defines a fixed two-feature GeoJSON
fixture and `mockDabsData(page, fc)`, which intercepts **every** `data/dabs-*.geojson`
request regardless of the requested filename's date. This is deliberate: the real
`data/*.geojson` files are dated, and tests must not depend on which day they happen to
run - don't swap this for real fixture files without re-adding that route interception.

Tests cover: initial render from fixture data, area selection (click + keyboard, including
the zoom-reliability regression and rapid-successive-click interruption), date tab
switching, language switching, and each collapsible panel's default state and
expand/collapse behavior. If you touch map view logic, run this suite before pushing -
it's what actually caught the `_animatingZoom` bug above; manual browser testing alone did
not reliably reproduce it.

## Things that look like bugs but aren't

- `notam` equals `id` when a feature's ID *is* a NOTAM number (no separate name was given
  in the PDF) - both fields get set to the same value in `dabs_parser.py`. Confirmed
  against real committed sample data, not a parsing error.
- `utc_iso(date, hhmm, end=False)` in `dabs_parser.py` has an unused `end` parameter.
  Harmless dead code, not worth a drive-by removal unless you're already editing that
  function for another reason.
