// EasyDABS front end — renders the GeoJSON produced by scripts/dabs_parser.py
// on an interactive, high-detail map instead of the low-res PDF chart.

const DATA_DIR = "../data";

const map = L.map("map", { minZoom: 6, maxZoom: 18 }).setView([46.82, 8.22], 8);

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
const officialLinkEl = document.getElementById("official-link");

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
  return `${CH_HM_FMT.format(from)}–${CH_HM_FMT.format(to)} ${chZoneLabel(from)} (${t("swissLocalTime")})`;
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
  return `
    <div class="area-popup">
      <h3>${props.id}<span class="badge ${badgeClass}">${badgeText}</span></h3>
      <dl>
        <dt>${t("popupValidity")}</dt><dd>${formatTimeRange(props.valid_from_utc, props.valid_to_utc)}</dd>
        <dt>${t("popupVertical")}</dt><dd>${formatAlt(props.lower)} &ndash; ${formatAlt(props.upper)}</dd>
        <dt>${t("popupShape")}</dt><dd>${geomNote}</dd>
        <dt>${t("popupNotam")}</dt><dd>${props.notam || "&ndash;"}</dd>
      </dl>
      <div class="notam-text-label">${t("notamOriginalNote")}</div>
      <div class="notam-text">${props.text}</div>
    </div>`;
}

function styleFor(feature) {
  const onChart = feature.properties.on_chart;
  const isCircle = feature.properties.geometry_source !== "polygon";
  return {
    color: onChart ? "#2563eb" : "#dc2626",
    weight: 2,
    fillColor: onChart ? "#2563eb" : "#dc2626",
    fillOpacity: 0.18,
    dashArray: isCircle ? "6 4" : null,
  };
}

let currentFc = null;

function renderFeatures(fc) {
  onChartLayer.clearLayers();
  notOnChartLayer.clearLayers();

  const p = fc.properties || {};
  metaEl.textContent = p.dabs_date
    ? `DABS ${p.dabs_date} · v${p.version} · ${t("generated")} ${formatSwissDateTime(p.generated_utc)}`
    : "";

  const bounds = [];
  for (const feature of fc.features) {
    const layer = L.geoJSON(feature, { style: styleFor });
    layer.bindPopup(popupHtml(feature.properties));
    (feature.properties.on_chart ? onChartLayer : notOnChartLayer).addLayer(layer);
    bounds.push(layer.getBounds());
  }

  if (bounds.length) {
    let combined = bounds[0];
    for (const b of bounds.slice(1)) combined = combined.extend(b);
    map.fitBounds(combined, { padding: [40, 40] });
  }
}

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
    tab.innerHTML = `<span class="day"></span><span class="ymd">${date}</span>`;
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
  }
  updateLangSwitchActive();
}

function updateLangSwitchActive() {
  for (const btn of langSwitchEl.querySelectorAll(".lang-btn")) {
    btn.classList.toggle("active", btn.dataset.lang === currentLang);
  }
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
