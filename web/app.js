// EasyDABS front end — renders the GeoJSON produced by scripts/dabs_parser.py
// on an interactive, high-detail map instead of the low-res PDF chart.

const DATA_DIR = "../data";
const IS_TOUCH = "ontouchstart" in window || navigator.maxTouchPoints > 0;

// app.js is deployed as "app.js?v=<short-sha>" (see .github/workflows/deploy-pages.yml);
// reuse that same version stamp to show which commit is live, instead of
// maintaining a separate version string.
const APP_VERSION = (() => {
  const src = document.currentScript && document.currentScript.src;
  const match = src && src.match(/[?&]v=([^&]+)/);
  return match ? match[1] : "dev";
})();

// keyboard:false avoids clashing with the area list's own Up/Down navigation,
// which would otherwise fire alongside Leaflet's built-in keyboard panning.
const map = L.map("map", { minZoom: 6, maxZoom: 18, keyboard: false }).setView([46.82, 8.22], 8);
map.attributionControl.setPrefix(`EasyDABS ${APP_VERSION}`);

// Leaflet caches the map container's pixel size and never re-measures it on
// its own, so any layout change that resizes #map (the collapsible legend
// and disclaimer, a window resize, an orientation change) leaves Leaflet
// panning/zooming against stale dimensions unless told to re-check.
new ResizeObserver(() => map.invalidateSize()).observe(document.getElementById("map"));

const swisstopo = L.tileLayer(
  "https://wmts10.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg",
  {
    maxZoom: 18,
    attribution: "&copy; swisstopo",
  }
).addTo(map);

const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
});

const onChartLayer = L.layerGroup().addTo(map);
const notOnChartLayer = L.layerGroup().addTo(map);

let layersControl = null;

function rebuildLayersControl() {
  if (layersControl) map.removeControl(layersControl);
  layersControl = L.control
    .layers(
      { [t("baseSwisstopo")]: swisstopo, [t("baseOsm")]: osm },
      { [t("overlayOnChart")]: onChartLayer, [t("overlayNotOnChart")]: notOnChartLayer }
    )
    .addTo(map);
}

const statusEl = document.getElementById("status");
const metaEl = document.getElementById("dabs-meta");
const tabsEl = document.getElementById("date-tabs");
const langSwitchEl = document.getElementById("lang-switch");
const langSelectEl = document.getElementById("lang-select");
const officialLinkEl = document.getElementById("official-link");
const areaListEl = document.getElementById("area-list");
const areaListTitleEl = document.getElementById("area-list-title");
const areaListHintEl = document.getElementById("area-list-hint");
const areaListPanelEl = document.getElementById("area-list-panel");
const areaListToggleEl = document.getElementById("area-list-toggle");

// Not a native <details>: its content (the scrollable area list) needs a
// flex/grid layout that shrinks to a max-height with an inner
// overflow-y:auto - and <details> does not let its hidden/shown content
// participate in that at all (verified directly: identical CSS on a plain
// div shrinks correctly, the exact same CSS inside <details> content always
// renders at full natural height, silently clipped by the panel's own
// overflow:hidden with no way to scroll to it). The [open] attribute is
// still used by hand so the rest of the CSS (written for <details>[open])
// needed no changes.
function setAreaListPanelOpen(open) {
  areaListPanelEl.toggleAttribute("open", open);
  areaListToggleEl.setAttribute("aria-expanded", String(open));
}

areaListToggleEl.addEventListener("click", () => {
  setAreaListPanelOpen(!areaListPanelEl.hasAttribute("open"));
});
areaListToggleEl.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  e.preventDefault();
  setAreaListPanelOpen(!areaListPanelEl.hasAttribute("open"));
});

// Open by default on desktop (where it sits beside the map at no cost to
// map space), collapsed by default on mobile (where the map is primary and
// screen space is scarce). Same breakpoint the layout itself switches on.
// Set once at load only - deliberately not re-applied on resize, so it
// never fights a user's manual toggle.
setAreaListPanelOpen(!window.matchMedia("(max-width: 760px)").matches);

function ymd(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

let currentStatus = null; // { key, vars } | null

function showStatus(key, vars) {
  currentStatus = { key, vars };
  statusEl.textContent = t(key, vars);
  statusEl.classList.remove("hidden");
}

function hideStatus() {
  currentStatus = null;
  statusEl.classList.add("hidden");
}

function formatAlt(limit) {
  if (!limit) return "?";
  if (limit.gnd) return "GND";
  if (limit.flight_level != null) return `FL${limit.flight_level}`;
  if (limit.meters != null) return `${limit.meters} m / ${limit.feet} ft`;
  return limit.raw;
}

const CH_HM_FMT = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Zurich",
});
const CH_DATETIME_FMT = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Zurich",
  timeZoneName: "short",
});

function chZoneLabel(date) {
  return CH_DATETIME_FMT.formatToParts(date).find((p) => p.type === "timeZoneName").value;
}

function formatTimeRange(fromIso, toIso) {
  const from = new Date(fromIso);
  const to = new Date(toIso);
  // 00:00 and 23:59 UTC are DABS's own "start/end of this day" sentinels,
  // not real instants - converting them faithfully to Swiss local time
  // would shift them by the UTC offset (e.g. 23:59 UTC rolling into
  // 01:59/00:59 the *next* calendar day), which misreads as "valid into
  // tomorrow"/"valid since yesterday" even though the source means "all
  // day, today". Show both as local 00:00/23:59 directly instead of doing
  // the timezone conversion.
  const isStartOfDay = from.getUTCHours() === 0 && from.getUTCMinutes() === 0;
  const isEndOfDay = to.getUTCHours() === 23 && to.getUTCMinutes() === 59;
  const fromDisplay = isStartOfDay ? "00:00" : CH_HM_FMT.format(from);
  const toDisplay = isEndOfDay ? "23:59" : CH_HM_FMT.format(to);
  return `${fromDisplay}–${toDisplay} ${chZoneLabel(from)} (${t("swissLocalTime")})`;
}

function formatSwissDateTime(iso) {
  return CH_DATETIME_FMT.format(new Date(iso));
}

function popupHtml(props) {
  const badgeClass = props.on_chart ? "chart" : "not-chart";
  const badgeText = props.on_chart ? t("popupOnChart") : t("popupNotOnChart");
  const geomNote =
    props.geometry_source === "polygon"
      ? t("shapePolygon")
      : t("shapeCircle", { km: (props.radius_m / 1000).toFixed(2) });
  // Only show the NOTAM number separately when it differs from the id -
  // for most areas the id already IS the NOTAM number (no separate name).
  const notamSuffix = props.notam && props.notam !== props.id ? ` (${props.notam})` : "";
  return `
    <div class="area-popup">
      <h3>${props.id}${notamSuffix}<span class="badge ${badgeClass}">${badgeText}</span></h3>
      <dl>
        <dt>${t("popupValidity")}</dt><dd>${formatTimeRange(props.valid_from_utc, props.valid_to_utc)}</dd>
        <dt>${t("popupVertical")}</dt><dd>${formatAlt(props.lower)} &ndash; ${formatAlt(props.upper)}</dd>
        <dt>${t("popupShape")}</dt><dd>${geomNote}</dd>
      </dl>
      <details class="notam-text-details">
        <summary>${t("notamOriginalNote")}</summary>
        <div class="notam-text">${props.text}</div>
      </details>
    </div>`;
}

function styleFor(feature) {
  const onChart = feature.properties.on_chart;
  const isCircle = feature.properties.geometry_source !== "polygon";
  return {
    color: onChart ? "#2563eb" : "#dc2626",
    weight: 2,
    fillColor: onChart ? "#2563eb" : "#dc2626",
    fillOpacity: 0.35,
    dashArray: isCircle ? "6 4" : null,
  };
}

const BLINK_FLASHES = 4;
const BLINK_INTERVAL_MS = 300;
const BLINK_STYLE = { fillOpacity: 0.85, weight: 5 };

function blinkLayer(layer, baseStyle) {
  let step = 0;
  const toggle = () => {
    layer.setStyle(step % 2 === 0 ? BLINK_STYLE : baseStyle);
    step++;
    if (step < BLINK_FLASHES * 2) {
      setTimeout(toggle, BLINK_INTERVAL_MS);
    } else {
      layer.setStyle(baseStyle);
    }
  };
  toggle();
}

let currentFc = null;
let currentAreas = []; // [{ feature, layer, baseStyle, itemEl }]
let selectedIndex = -1;

function renderFeatures(fc) {
  onChartLayer.clearLayers();
  notOnChartLayer.clearLayers();
  areaListEl.innerHTML = "";
  currentAreas = [];
  selectedIndex = -1;

  const p = fc.properties || {};
  metaEl.textContent = p.dabs_date
    ? `DABS ${p.dabs_date} · v${p.version} · ${t("generated")} ${formatSwissDateTime(p.generated_utc)}`
    : "";

  const features = [...fc.features].sort((a, b) =>
    a.properties.valid_from_utc.localeCompare(b.properties.valid_from_utc)
  );

  const bounds = [];
  features.forEach((feature, index) => {
    const baseStyle = styleFor(feature);
    const layer = L.geoJSON(feature, { style: baseStyle });
    layer.bindPopup(popupHtml(feature.properties), { maxWidth: Math.min(300, window.innerWidth - 40) });
    layer.on("click", () => selectArea(index, { fly: false }));
    (feature.properties.on_chart ? onChartLayer : notOnChartLayer).addLayer(layer);
    bounds.push(layer.getBounds());
    blinkLayer(layer, baseStyle);

    const itemEl = buildAreaListItem(feature, index);
    areaListEl.appendChild(itemEl);
    currentAreas.push({ feature, layer, baseStyle, itemEl });
  });

  if (!features.length) {
    const empty = document.createElement("li");
    empty.className = "area-list-empty";
    empty.textContent = t("areaListEmpty");
    areaListEl.appendChild(empty);
  }

  if (bounds.length) {
    let combined = bounds[0];
    for (const b of bounds.slice(1)) combined = combined.extend(b);
    // animate:false for the same reason as selectArea's setView below: an
    // animated zoom here can leave Leaflet's internal _animatingZoom flag
    // stuck true forever if its CSS transitionend never fires (observed in
    // headless/backgrounded-tab conditions), silently blocking every zoom
    // change for the rest of the page's life - including the deliberately
    // non-animated calls elsewhere, since Leaflet won't start a new view
    // change while it still thinks one is in flight.
    map.fitBounds(combined, { padding: [40, 40], animate: false });
  }
}

function buildAreaListItem(feature, index) {
  const props = feature.properties;
  const li = document.createElement("li");
  li.className = "area-item";

  const swatch = document.createElement("span");
  swatch.className = `swatch ${props.on_chart ? "chart" : "not-chart"}`;
  swatch.title = props.on_chart ? t("popupOnChart") : t("popupNotOnChart");

  const text = document.createElement("div");
  text.className = "area-item-text";
  const idEl = document.createElement("div");
  idEl.className = "area-item-id";
  idEl.textContent = props.id;
  const timeEl = document.createElement("div");
  timeEl.className = "area-item-time";
  timeEl.textContent = formatTimeRange(props.valid_from_utc, props.valid_to_utc);
  text.append(idEl, timeEl);

  li.append(swatch, text);
  li.addEventListener("click", () => selectArea(index, { fly: true }));
  return li;
}

function selectArea(index, { fly }) {
  if (index < 0 || index >= currentAreas.length) return;
  if (selectedIndex >= 0 && currentAreas[selectedIndex]) {
    currentAreas[selectedIndex].itemEl.classList.remove("active");
  }
  selectedIndex = index;
  const area = currentAreas[index];
  area.itemEl.classList.add("active");
  area.itemEl.scrollIntoView({ block: "nearest" });
  if (fly) {
    // Not animated: both flyTo and setView's animated zoom proved unreliable
    // here - their animation can take far longer than requested to settle,
    // or never visibly complete, especially when a new call interrupts one
    // still in flight (exactly what happens clicking through the list
    // quickly). An instant jump is less polished but always correct.
    //
    // A fixed zoom (rather than fitting area.layer's bounds) keeps this
    // viewport-independent: fitting bounds with fixed pixel padding zooms
    // out much further on a narrow window, since the padding eats a bigger
    // share of the screen. All areas are small (1-4km radius) so a constant
    // zoom works for every one.
    map.setView(area.layer.getBounds().getCenter(), 7, { animate: false });
  }
  area.layer.openPopup();
  blinkLayer(area.layer, area.baseStyle);
}

function moveSelection(delta) {
  if (!currentAreas.length) return;
  const n = currentAreas.length;
  const next = selectedIndex < 0 ? 0 : (selectedIndex + delta + n) % n;
  selectArea(next, { fly: true });
}

document.addEventListener("keydown", (e) => {
  if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  e.preventDefault();
  moveSelection(e.key === "ArrowDown" ? 1 : -1);
});

async function loadDate(date) {
  hideStatus();
  metaEl.textContent = "";
  currentFc = null;
  onChartLayer.clearLayers();
  notOnChartLayer.clearLayers();

  const url = `${DATA_DIR}/dabs-${date}.geojson`;
  let res;
  try {
    res = await fetch(url);
  } catch (e) {
    showStatus("statusNoFetch", { date });
    return;
  }
  if (!res.ok) {
    showStatus("statusNoData", { date });
    return;
  }

  const fc = await res.json();
  currentFc = fc;
  renderFeatures(fc);

  if (!fc.features.length) {
    showStatus("statusEmpty", { date });
  }
}

function formatTabDate(isoDate) {
  const [y, m, d] = isoDate.split("-");
  return `${d}.${m}.${y}`;
}

function buildTabs() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (let offset = 0; offset <= 1; offset++) {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    const date = ymd(d);

    const tab = document.createElement("button");
    tab.className = "date-tab";
    tab.dataset.date = date;
    tab.dataset.offset = offset;
    tab.innerHTML = `<span class="day"></span><span class="ymd">${formatTabDate(date)}</span>`;
    tab.addEventListener("click", () => selectTab(date, offset));
    tabsEl.appendChild(tab);
  }
  applyTabLabels();
}

function applyTabLabels() {
  for (const tab of tabsEl.querySelectorAll(".date-tab")) {
    const offset = Number(tab.dataset.offset);
    tab.querySelector(".day").textContent = offset === 0 ? t("today") : t("tomorrow");
  }
}

function selectTab(date, offset) {
  for (const tab of tabsEl.querySelectorAll(".date-tab")) {
    tab.classList.toggle("active", tab.dataset.date === date);
  }
  officialLinkEl.href = `https://www.skybriefing.com/o/dabs?${offset === 0 ? "today" : "tomorrow"}`;
  loadDate(date);
}

function applyStaticTranslations() {
  document.getElementById("legend-title").textContent = t("legendTitle");
  document.getElementById("legend-on-chart").textContent = t("legendOnChart");
  document.getElementById("legend-not-on-chart").textContent = t("legendNotOnChart");
  document.getElementById("legend-polygon").textContent = t("legendPolygon");
  document.getElementById("legend-circle").textContent = t("legendCircle");

  document.getElementById("disclaimer-label").textContent = t("disclaimerLabel");
  document.getElementById("disclaimer-text").textContent = t("disclaimerText");
  officialLinkEl.textContent = t("officialSourceLink");
  document.getElementById("disclaimer-tz-prefix").textContent = t("disclaimerTimezonePrefix");
  document.getElementById("disclaimer-tz-bold").textContent = t("swissLocalTime");
  document.getElementById("disclaimer-tz-suffix").textContent = t("disclaimerTimezoneSuffix");

  areaListTitleEl.textContent = t("areaListTitle");
  areaListHintEl.textContent = t(IS_TOUCH ? "areaListHintTouch" : "areaListHint");

  applyTabLabels();
  rebuildLayersControl();
}

function buildLangSwitch() {
  for (const lang of SUPPORTED_LANGS) {
    const btn = document.createElement("button");
    btn.className = "lang-btn";
    btn.textContent = LANG_NAMES[lang];
    btn.dataset.lang = lang;
    btn.addEventListener("click", () => {
      setLang(lang);
      refreshUi();
    });
    langSwitchEl.appendChild(btn);

    const option = document.createElement("option");
    option.value = lang;
    option.textContent = LANG_NAMES[lang];
    langSelectEl.appendChild(option);
  }
  langSelectEl.addEventListener("change", () => {
    setLang(langSelectEl.value);
    refreshUi();
  });
  updateLangSwitchActive();
}

function updateLangSwitchActive() {
  for (const btn of langSwitchEl.querySelectorAll(".lang-btn")) {
    btn.classList.toggle("active", btn.dataset.lang === currentLang);
  }
  langSelectEl.value = currentLang;
}

function refreshUi() {
  updateLangSwitchActive();
  applyStaticTranslations();
  if (currentFc) {
    renderFeatures(currentFc);
    if (!currentFc.features.length) showStatus("statusEmpty", currentStatus?.vars);
  } else if (currentStatus) {
    showStatus(currentStatus.key, currentStatus.vars);
  }
}

document.documentElement.lang = currentLang;
buildLangSwitch();
buildTabs();
applyStaticTranslations();
const firstTab = tabsEl.querySelector(".date-tab");
selectTab(firstTab.dataset.date, Number(firstTab.dataset.offset));
