const $ = (id) => document.getElementById(id);
const MODE = new URLSearchParams(location.search).get("mode") === "demo" ? "demo" : "live";
const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
const REFRESH_MS = 60_000;

const compass = (deg) => deg == null ? "" : ` ${COMPASS[Math.round(deg / 45) % 8]}`;
const when = (iso) => new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function entry(e) {
  const d = e.decision;
  const li = el("li", `entry ${d.status}${e.changed_from ? " changed" : ""}`);

  const top = el("div", "entry-top");
  top.append(el("span", `pill ${d.status}`, d.status), el("time", "muted small", when(e.reading.timestamp)));
  if (e.changed_from) top.append(el("span", "change small", `${e.changed_from} → ${d.status}`));
  li.append(top);

  li.append(el("div", "small", [e.pesticide, e.nozzle].filter(Boolean).join(" · ")));
  const levels = e.reading.levels.length
    ? [...e.reading.levels].reverse().map((lv) => `${lv.height_ft} ft: ${lv.temp_f.toFixed(1)}°F, ${lv.wind_mph.toFixed(1)} mph${compass(lv.wind_dir_deg)}`).join("  ·  ")
    : "No weather data";
  li.append(el("div", "muted small", levels));

  if (d.flags.length) {
    const det = el("details");
    det.append(el("summary", "small", `Triggered: ${[...new Set(d.flags.map((f) => f.check.replace(/_/g, " ")))].join(", ")}`));
    const ul = el("ul", "reasons");
    for (const f of d.flags) {
      const r = el("li", f.severity);
      r.append(el("span", "tag", `${f.severity} · ${f.check.replace(/_/g, " ")}`), f.reason);
      ul.append(r);
    }
    det.append(ul);
    li.append(det);
  } else {
    li.append(el("div", "muted small", "No alerts"));
  }
  li.append(el("div", "muted tiny", `Source: ${e.reading.source}`));
  return li;
}

async function load() {
  const changes = $("changes-only").checked;
  try {
    const res = await fetch(`/api/log?mode=${MODE}&changes_only=${changes}`);
    const items = await res.json();
    $("entries").replaceChildren(...items.map(entry));
    $("empty").hidden = items.length > 0;
  } catch {
    $("empty").hidden = false;
    $("empty").textContent = "Couldn't load the log. Check your connection.";
  }
}

$(`tab-${MODE}`).classList.add("active");
$(`tab-${MODE}`).setAttribute("aria-current", "page");
$("back").href = MODE === "demo" ? "/demo" : "/";
$("csv").href = `/api/log.csv?mode=${MODE}`;
$("changes-only").addEventListener("change", load);
load();
setInterval(load, REFRESH_MS);
