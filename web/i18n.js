// Translations for EasyDABS UI chrome. NOTAM text itself is deliberately left
// untranslated everywhere — ICAO convention mandates NOTAMs in English, and a
// machine translation of safety-critical airspace text would be dangerous.

const SUPPORTED_LANGS = ["en", "fr", "de", "it"];
const LANG_NAMES = { en: "EN", fr: "FR", de: "DE", it: "IT" };

const TRANSLATIONS = {
  en: {
    legendTitle: "Legend",
    legendOnChart: "On chart (shown on official DABS map)",
    legendNotOnChart: "Not on chart (extra detail, hidden on the PDF map)",
    legendPolygon: "Exact polygon (from NOTAM text)",
    legendCircle: "Approximate circle (radius only)",
    today: "Today",
    tomorrow: "Tomorrow",
    disclaimerLabel: "Disclaimer:",
    disclaimerText:
      "provided for situational awareness only, without any guarantee of accuracy or completeness. The official Skybriefing DABS publication remains the sole source of truth —",
    officialSourceLink: "view official source",
    disclaimerTimezonePrefix: "All dates/times shown are",
    disclaimerTimezoneSuffix: ", not UTC.",
    swissLocalTime: "Swiss local time",
    generated: "generated",
    popupOnChart: "on chart",
    popupNotOnChart: "not on chart",
    popupValidity: "Validity",
    popupVertical: "Vertical",
    popupShape: "Shape",
    popupNotam: "NOTAM",
    shapePolygon: "Exact polygon from NOTAM text",
    shapeCircle: "Approximate circle, radius {km} km",
    notamOriginalNote: "Original NOTAM text (English, per ICAO convention)",
    statusNoFetch: "Could not reach data for {date}",
    statusNoData: "No DABS data published yet for {date}",
    statusEmpty: "DABS {date} published but contains no restricted areas",
    baseSwisstopo: "Swisstopo (detailed)",
    baseOsm: "OpenStreetMap",
    overlayOnChart: "On official chart",
    overlayNotOnChart: "Not on official chart",
  },
  fr: {
    legendTitle: "Légende",
    legendOnChart: "Sur la carte (affiché sur la carte DABS officielle)",
    legendNotOnChart: "Hors carte (détail supplémentaire, absent de la carte PDF)",
    legendPolygon: "Polygone exact (texte du NOTAM)",
    legendCircle: "Cercle approximatif (rayon uniquement)",
    today: "Aujourd'hui",
    tomorrow: "Demain",
    disclaimerLabel: "Avertissement :",
    disclaimerText:
      "fourni à titre indicatif uniquement, sans aucune garantie d'exactitude ou d'exhaustivité. La publication DABS officielle de Skybriefing reste la seule source faisant foi —",
    officialSourceLink: "voir la source officielle",
    disclaimerTimezonePrefix: "Toutes les dates/heures affichées sont en",
    disclaimerTimezoneSuffix: ", pas en UTC.",
    swissLocalTime: "heure locale suisse",
    generated: "généré le",
    popupOnChart: "sur la carte",
    popupNotOnChart: "hors carte",
    popupValidity: "Validité",
    popupVertical: "Vertical",
    popupShape: "Forme",
    popupNotam: "NOTAM",
    shapePolygon: "Polygone exact d'après le texte du NOTAM",
    shapeCircle: "Cercle approximatif, rayon {km} km",
    notamOriginalNote: "Texte NOTAM original (anglais, convention OACI)",
    statusNoFetch: "Impossible d'accéder aux données pour le {date}",
    statusNoData: "Aucune donnée DABS publiée pour le {date}",
    statusEmpty: "DABS du {date} publié mais ne contient aucune zone restreinte",
    baseSwisstopo: "Swisstopo (détaillé)",
    baseOsm: "OpenStreetMap",
    overlayOnChart: "Sur la carte officielle",
    overlayNotOnChart: "Hors carte officielle",
  },
  de: {
    legendTitle: "Legende",
    legendOnChart: "Auf der Karte (auf der offiziellen DABS-Karte dargestellt)",
    legendNotOnChart: "Nicht auf der Karte (zusätzliche Details, in der PDF-Karte nicht sichtbar)",
    legendPolygon: "Exaktes Polygon (aus NOTAM-Text)",
    legendCircle: "Angenäherter Kreis (nur Radius)",
    today: "Heute",
    tomorrow: "Morgen",
    disclaimerLabel: "Haftungsausschluss:",
    disclaimerText:
      "dient nur der allgemeinen Orientierung, ohne Gewähr für Richtigkeit oder Vollständigkeit. Die offizielle Skybriefing-DABS-Publikation bleibt die massgebliche Quelle —",
    officialSourceLink: "offizielle Quelle ansehen",
    disclaimerTimezonePrefix: "Alle angezeigten Daten/Zeiten sind in",
    disclaimerTimezoneSuffix: ", nicht UTC.",
    swissLocalTime: "Schweizer Lokalzeit",
    generated: "erstellt am",
    popupOnChart: "auf der Karte",
    popupNotOnChart: "nicht auf der Karte",
    popupValidity: "Gültigkeit",
    popupVertical: "Vertikal",
    popupShape: "Form",
    popupNotam: "NOTAM",
    shapePolygon: "Exaktes Polygon aus dem NOTAM-Text",
    shapeCircle: "Angenäherter Kreis, Radius {km} km",
    notamOriginalNote: "Original-NOTAM-Text (Englisch, gemäss ICAO-Konvention)",
    statusNoFetch: "Daten für {date} konnten nicht abgerufen werden",
    statusNoData: "Für {date} wurden noch keine DABS-Daten veröffentlicht",
    statusEmpty: "DABS {date} veröffentlicht, enthält aber keine Sperrgebiete",
    baseSwisstopo: "Swisstopo (detailliert)",
    baseOsm: "OpenStreetMap",
    overlayOnChart: "Auf der offiziellen Karte",
    overlayNotOnChart: "Nicht auf der offiziellen Karte",
  },
  it: {
    legendTitle: "Legenda",
    legendOnChart: "Sulla carta (mostrato sulla carta DABS ufficiale)",
    legendNotOnChart: "Non sulla carta (dettaglio aggiuntivo, assente dalla carta PDF)",
    legendPolygon: "Poligono esatto (dal testo NOTAM)",
    legendCircle: "Cerchio approssimativo (solo raggio)",
    today: "Oggi",
    tomorrow: "Domani",
    disclaimerLabel: "Avvertenza:",
    disclaimerText:
      "fornito solo a scopo informativo, senza alcuna garanzia di accuratezza o completezza. La pubblicazione DABS ufficiale di Skybriefing resta l'unica fonte autorevole —",
    officialSourceLink: "vedi fonte ufficiale",
    disclaimerTimezonePrefix: "Tutte le date/ore mostrate sono in",
    disclaimerTimezoneSuffix: ", non UTC.",
    swissLocalTime: "ora locale svizzera",
    generated: "generato il",
    popupOnChart: "sulla carta",
    popupNotOnChart: "non sulla carta",
    popupValidity: "Validità",
    popupVertical: "Verticale",
    popupShape: "Forma",
    popupNotam: "NOTAM",
    shapePolygon: "Poligono esatto dal testo NOTAM",
    shapeCircle: "Cerchio approssimativo, raggio {km} km",
    notamOriginalNote: "Testo NOTAM originale (inglese, convenzione ICAO)",
    statusNoFetch: "Impossibile recuperare i dati per il {date}",
    statusNoData: "Nessun dato DABS pubblicato per il {date}",
    statusEmpty: "DABS del {date} pubblicato ma non contiene aree riservate",
    baseSwisstopo: "Swisstopo (dettagliato)",
    baseOsm: "OpenStreetMap",
    overlayOnChart: "Sulla carta ufficiale",
    overlayNotOnChart: "Non sulla carta ufficiale",
  },
};

function detectLang() {
  const stored = localStorage.getItem("easydabs-lang");
  if (stored && SUPPORTED_LANGS.includes(stored)) return stored;
  const nav = (navigator.language || "en").slice(0, 2).toLowerCase();
  return SUPPORTED_LANGS.includes(nav) ? nav : "en";
}

let currentLang = detectLang();

function t(key, vars) {
  let str = (TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key]) || TRANSLATIONS.en[key] || key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) str = str.replace(`{${k}}`, v);
  }
  return str;
}

function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) return;
  currentLang = lang;
  localStorage.setItem("easydabs-lang", lang);
  document.documentElement.lang = lang;
}
