const $ = (id) => document.getElementById(id);
const DEMO = location.pathname.startsWith("/demo");
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};
const SUBTITLE = { GO: "Conditions look good to spray", CAUTION: "Spray with care", STOP: "Do not spray now" };
const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
const PUBLIC = "__public__";
const STATION = "__station__";
const REFRESH_MS = 60_000;
let scenarios = [];
let lastStatus = null;
const RANK = { GO: 0, CAUTION: 1, STOP: 2 };
let coords = null;

async function api(path, body) {
  const res = await fetch(path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

// The pesticide is typed (with suggestions); a name only counts if it matches a known one.
const known = { pesticide: [] };
const applied = { pesticide: null };

function fillList(kind, items, saved) {
  known[kind] = items.map((i) => i.value);
  $(`${kind}-list`).replaceChildren(...items.map(({ value, label }) => {
    const o = document.createElement("option");
    o.value = value;
    if (label !== value) o.label = label;
    return o;
  }));
  $(kind).value = known[kind].includes(saved) ? saved : known[kind][0] || "";
  applied[kind] = $(kind).value;
}

/** The known name matching what was typed (ignoring case and extra spaces), or null. */
function canonical(kind) {
  const typed = $(kind).value.trim().replace(/\s+/g, " ").toLowerCase();
  return known[kind].find((n) => n.toLowerCase() === typed) ?? null;
}

function setupTyped(kind) {
  const input = $(kind);
  // Clear on focus so the full suggestion list shows; put the last good value back if nothing is chosen.
  input.addEventListener("focus", () => {
    input.placeholder = applied[kind] ? `Type to search (now: ${applied[kind]})` : "Type a pesticide name";
    input.value = "";
  });
  input.addEventListener("blur", () => { if (!input.value.trim()) input.value = applied[kind] || ""; });
  const apply = (final) => {
    const name = canonical(kind);
    $(`${kind}-err`).hidden = !!name || !final || !input.value.trim();
    $(`${kind}-err`).textContent = `No ${kind} called "${input.value.trim()}". Keep typing and tap a name in the list. Still using ${applied[kind]}.`;
    if (name && name !== applied[kind]) { input.value = name; applied[kind] = name; update(); }
  };
  input.addEventListener("input", () => apply(false));  // picking a suggestion applies at once
  input.addEventListener("change", () => apply(true));
}

function fillSelect(sel, items, saved) {
  sel.replaceChildren(...items.map(({ value, label }) => new Option(label, value)));
  if (saved && items.some((i) => i.value === saved)) sel.value = saved;
}

const compass = (deg) => deg == null ? "–" : COMPASS[Math.round(deg / 45) % 8];
const clock = (iso) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

function showError(word, msg) {
  $("status").className = "status error";
  $("status").querySelector(".status-word").textContent = word;
  $("status").querySelector(".status-sub").textContent = msg;
}

function render(data) {
  const d = data.decision;
  if (lastStatus && RANK[d.status] > RANK[lastStatus]) alertChange(lastStatus, d);  // only when it gets worse
  else if (lastStatus && RANK[d.status] < RANK[lastStatus]) $("alert").hidden = true;  // improved: old alert is stale
  lastStatus = d.status;
  $("status").className = `status ${d.status}`;
  $("status").querySelector(".status-word").textContent = d.status;
  $("status").querySelector(".status-sub").textContent = SUBTITLE[d.status];
  $("source").textContent = `Weather: ${data.reading.source} · ${clock(data.reading.timestamp)}`;

  const items = d.flags.length
    ? d.flags.map((f) => ({ cls: f.severity, tag: f.check.replace(/_/g, " "), text: f.reason }))
    : d.reasons.map((r) => ({ cls: "GO", tag: "all clear", text: r }));
  $("reasons").replaceChildren(...items.map(({ cls, tag, text }) => {
    const li = document.createElement("li");
    li.className = cls;
    const t = document.createElement("span");
    t.className = "tag";
    t.textContent = tag;
    li.append(t, text);
    return li;
  }));

  const g = data.ground_only?.status;
  $("compare").hidden = !DEMO || !g || g === d.status;  // pitch line: demo mode only
  $("compare").textContent = `A ground-level station alone would say ${g}. Measuring above the canopy changes the answer.`;

  $("levels-section").hidden = !data.reading.levels.length;
  $("levels").replaceChildren(...[...data.reading.levels].reverse().map((lv) => {
    const tr = document.createElement("tr");
    for (const v of [`${lv.height_ft} ft`, `${lv.temp_f.toFixed(1)}°F`, `${lv.wind_mph.toFixed(1)} mph`, compass(lv.wind_dir_deg)]) {
      tr.insertCell().textContent = v;
    }
    return tr;
  }));
}

// Alert when conditions worsen (GO→CAUTION/STOP, CAUTION→STOP): in-page banner, vibration (Android), and a system notification if allowed.
const canNotify = "Notification" in window && "serviceWorker" in navigator;

function alertChange(from, d) {
  const title = `${from} → ${d.status}: ${SUBTITLE[d.status]}`;
  const text = d.flags[0]?.reason || d.reasons[0] || "";
  $("alert").className = `alert ${d.status}`;
  $("alert-title").textContent = title;
  $("alert-text").textContent = text;
  $("alert").hidden = false;
  navigator.vibrate?.([200, 100, 200]);
  if (canNotify && Notification.permission === "granted") {
    navigator.serviceWorker.ready
      .then((reg) => reg.showNotification(title, { body: text, tag: "spray-status", renotify: true, icon: "/icons/icon-192.png" }))
      .catch(() => {});
  }
}

function setupAlerts() {
  $("alert-close").addEventListener("click", () => { $("alert").hidden = true; });
  if (!canNotify || Notification.permission !== "default") return;
  $("enable-alerts").hidden = false;
  $("enable-alerts").addEventListener("click", async () => {
    await Notification.requestPermission().catch(() => {});
    $("enable-alerts").hidden = true;
  });
}

// Next 24 h forecast strip and next spray window.
const hourLabel = (iso) => new Date(iso).toLocaleTimeString([], { hour: "numeric" });
const dayHour = (iso) => new Date(iso).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" });
const dayLabel = (iso) => new Date(iso).toLocaleDateString([], { weekday: "short" });
const checkNames = (c) => c.map((x) => x.replace(/_/g, " ")).join(", ");

function forecastSummary(f) {
  const now = f.hours[0]?.status;
  if (!now) return "No forecast available.";
  if (now === "GO") {
    return f.worsens
      ? `Good to spray now. Expected to turn ${f.worsens.status} around ${dayHour(f.worsens.time)} (${checkNames(f.worsens.checks)}).`
      : "Good to spray for the next 24 hours.";
  }
  if (f.next_go) return `Next GO window: ${dayLabel(f.next_go.start)} ${hourLabel(f.next_go.start)} – ${hourLabel(f.next_go.end)}.`;
  return "No GO window in the next 24 hours.";
}

function renderForecast(f) {
  $("forecast").hidden = false;
  $("forecast-summary").textContent = forecastSummary(f);
  const detail = (h) => `${dayHour(h.time)}: ${h.status}${h.checks.length ? ` (${checkNames(h.checks)})` : ""}`;
  $("forecast-strip").replaceChildren(...f.hours.map((h) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = h.status;
    b.setAttribute("role", "listitem");
    b.setAttribute("aria-label", detail(h));
    b.title = detail(h);
    b.addEventListener("click", () => {
      $("forecast-strip").querySelectorAll(".sel").forEach((x) => x.classList.remove("sel"));
      b.classList.add("sel");
      $("forecast-detail").textContent = detail(h);
    });
    return b;
  }));
  $("forecast-ticks").replaceChildren(...f.hours.map((h, i) => {
    const s = document.createElement("span");
    s.textContent = i % 6 === 0 ? hourLabel(h.time) : "";
    return s;
  }));
}

// The browser fetches the forecast itself (its own IP; the shared host IP gets rate-limited),
// at most every 30 min, then the server runs the checks on it.
const FORECAST_TTL_MS = 30 * 60_000;
let hourly = null, hourlyAt = 0, lastForecast = null;

async function fetchHourly() {
  if (hourly && Date.now() - hourlyAt < FORECAST_TTL_MS) return hourly;
  const { forecast_url } = await api("/api/orchard");
  const res = await fetch(forecast_url);
  if (!res.ok) throw new Error(`forecast ${res.status}`);
  hourly = (await res.json()).hourly;
  hourlyAt = Date.now();
  return hourly;
}

async function updateForecast(pesticide, nozzle) {
  try {
    lastForecast = await api("/api/forecast", { pesticide, nozzle, hourly: await fetchHourly() });
    renderForecast(lastForecast);
  } catch {
    // Keep the last good forecast on a hiccup; with none, hide it (the live decision still stands).
    if (!lastForecast) $("forecast").hidden = true;
  }
}

function locate() {
  if (coords) return Promise.resolve(coords);
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("location not available on this device"));
    navigator.geolocation.getCurrentPosition(
      (p) => resolve(coords = { lat: p.coords.latitude, lon: p.coords.longitude }),
      () => reject(new Error("location permission denied")),
      { timeout: 10_000, maximumAge: 600_000 },
    );
  });
}

async function weatherQuery() {
  if (!DEMO) return { source: "farm" };
  const scenario = $("scenario").value;
  if (scenario === PUBLIC) return { source: "public", ...(await locate()) };
  if (scenario === STATION) return { source: "station" };
  return { source: "simulated", scenario };
}

async function update() {
  const pesticide = applied.pesticide, nozzle = $("nozzle").value;
  store.set("pesticide", pesticide);
  store.set("nozzle", nozzle);
  if (DEMO) {
    store.set("scenario", $("scenario").value);
    const s = scenarios.find((x) => x.id === $("scenario").value);
    $("demo-note-text").textContent = s?.illustrates || "";
    $("demo-note-expect").hidden = !s?.expect;
    if (s?.expect) {
      $("demo-note-expect").textContent =
        `Expected with the generic label: ground station alone ${s.expect.ground} · SprayWait ${s.expect.spraywait}`;
    }
  }
  updateForecast(pesticide, nozzle);
  try {
    render(await api("/api/decision", { pesticide, nozzle, ...(await weatherQuery()) }));
  } catch (e) {
    showError("?", `Couldn't get a decision: ${e.message}`);
  }
}

async function init() {
  if (DEMO) {
    $("mode-badge").hidden = false;
    $("scenario-field").hidden = false;
    $("demo-note").hidden = false;
    $("mode-link").href = "/";
    $("log-link").href = "/log?mode=demo";
    $("mode-link").textContent = "Live";
  }
  const [pesticides, nozzles, scen] = await Promise.all([
    api("/api/pesticides"), api("/api/nozzles"), DEMO ? api("/api/scenarios") : [],
  ]);
  scenarios = [
    ...scen,
    { id: STATION, title: "Farm station (simulated, live clock)", illustrates: "A full day on a 5 ft / 30 ft mast: the weather follows the clock, with inversions at night and mixing by day." },
    { id: PUBLIC, title: "Public forecast near me", illustrates: "The same checks on forecast-model weather at your location (2 m and 80 m), for orchards without a station." }];
  fillList("pesticide", pesticides.map((p) => ({ value: p.name, label: p.category ? `${p.name} (${p.category})` : p.name })), store.get("pesticide"));
  fillSelect($("nozzle"), nozzles.map((n) => ({ value: n.name, label: `${n.name} (${n.asabe_class})` })), store.get("nozzle"));
  if (DEMO) fillSelect($("scenario"), scenarios.map((s) => ({ value: s.id, label: s.title })), store.get("scenario"));
  setupTyped("pesticide");
  $("nozzle").addEventListener("change", update);
  $("scenario").addEventListener("change", update);
  setupAlerts();
  await update();
  if (!DEMO) setInterval(update, REFRESH_MS);
}

init().catch((e) => showError("?", `Offline or server down: ${e.message}`));

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
