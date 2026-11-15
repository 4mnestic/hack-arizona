const $ = (id) => document.getElementById(id);
const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
const REFRESH_MS = 30_000;
const GAP_MS = 11 * 60_000; // break the line when reports are missing
const W = 520, PAD = { l: 34, r: 44, t: 8, b: 20 };
const NS = "http://www.w3.org/2000/svg";
let points = [];

const compass = (deg) => deg == null ? "–" : COMPASS[Math.round(deg / 45) % 8];
const clock = (t) => new Date(t).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
const fmt = (v, u) => v == null ? "–" : `${v.toFixed(1)}${u}`;

function el(tag, attrs = {}, text) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text != null) e.textContent = text;
  return e;
}

function td(text) {
  const c = document.createElement("td");
  c.textContent = text;
  return c;
}

/** Flatten an API point to {t, lo, hi, status, checks}; lo/hi are the lowest/highest levels. */
function toPoint(p) {
  const lv = p.levels;
  return { t: Date.parse(p.timestamp), lo: lv[0] ?? null, hi: lv.length > 1 ? lv[lv.length - 1] : null, status: p.status, checks: p.checks };
}

function scale(d0, d1, r0, r1) {
  const k = (r1 - r0) / (d1 - d0 || 1);
  const f = (v) => r0 + (v - d0) * k;
  f.invert = (px) => d0 + (px - r0) / k;
  return f;
}

function niceTicks(min, max, n = 4) {
  const step = Math.pow(10, Math.floor(Math.log10((max - min) / n || 1)));
  const s = [1, 2, 5, 10].map((m) => m * step).find((x) => (max - min) / x <= n) ?? step * 10;
  const out = [];
  for (let v = Math.ceil(min / s) * s; v <= max + 1e-9; v += s) out.push(+v.toFixed(6));
  return out;
}

function timeTicks(t0, t1) {
  const hours = (t1 - t0) / 3.6e6;
  const step = [1, 2, 3, 6].find((h) => hours / h <= 6) ?? 12;
  const d = new Date(t0);
  d.setMinutes(0, 0, 0);
  const out = [];
  for (let t = d.getTime(); t <= t1; t += step * 3.6e6) if (t >= t0) out.push(t);
  return out;
}

/** Line path that breaks where readings are missing or more than GAP_MS apart. */
function path(pts, x, y) {
  let d = "", prev = null;
  for (const p of pts) {
    if (p.v == null) { prev = null; continue; }
    d += `${prev && p.t - prev.t <= GAP_MS ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`;
    prev = p;
  }
  return d;
}

/** Two-series line chart (5 ft, 30 ft) with optional shaded bands. Returns the x scale for hover. */
function lineChart(fig, key, unit, bands) {
  const H = 170;
  const lo = points.map((p) => ({ t: p.t, v: p.lo?.[key] ?? null }));
  const hi = points.map((p) => ({ t: p.t, v: p.hi?.[key] ?? null }));
  const vals = [...lo, ...hi].map((p) => p.v).filter((v) => v != null);
  const extra = bands.flatMap((b) => b.y ?? []);
  let min = Math.min(...vals, ...extra), max = Math.max(...vals, ...extra);
  const padY = Math.max(0.5, (max - min) * 0.1);
  min -= padY; max += padY;
  const t0 = points[0].t, t1 = Math.max(points[points.length - 1].t, t0 + 3.6e6);
  const x = scale(t0, t1, PAD.l, W - PAD.r), y = scale(min, max, H - PAD.b, PAD.t);

  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${unit} at 5 ft and 30 ft over time` });
  for (const b of bands) {
    if (b.y) svg.append(el("rect", { class: b.cls, x: PAD.l, width: W - PAD.l - PAD.r, y: y(Math.min(b.y[1], max)), height: Math.max(0, y(Math.max(b.y[0], min)) - y(Math.min(b.y[1], max))) }));
    if (b.when) for (const p of points) if (b.when(p)) svg.append(el("rect", { class: b.cls, x: x(p.t) - 2, width: Math.max(4, x(p.t + 300_000) - x(p.t)), y: PAD.t, height: H - PAD.t - PAD.b }));
  }
  for (const v of niceTicks(min, max)) {
    svg.append(el("line", { class: "grid", x1: PAD.l, x2: W - PAD.r, y1: y(v), y2: y(v) }));
    svg.append(el("text", { x: PAD.l - 6, y: y(v) + 4, "text-anchor": "end" }, String(v)));
  }
  for (const t of timeTicks(t0, t1)) svg.append(el("text", { x: x(t), y: H - 4, "text-anchor": "middle" }, clock(t)));
  svg.append(el("path", { class: "line l1", d: path(lo, x, y) }), el("path", { class: "line l2", d: path(hi, x, y) }));

  // Direct labels at the latest values, nudged apart if they collide.
  const lastLo = [...lo].reverse().find((p) => p.v != null), lastHi = [...hi].reverse().find((p) => p.v != null);
  const ends = [[lastLo, "5 ft"], [lastHi, "30 ft"]].filter(([p]) => p).map(([p, label]) => ({ p, label, ly: y(p.v) + 4 }));
  if (ends.length === 2 && Math.abs(ends[0].ly - ends[1].ly) < 12) {
    const [a, b] = ends[0].ly < ends[1].ly ? ends : [ends[1], ends[0]];
    const mid = (a.ly + b.ly) / 2; a.ly = mid - 6; b.ly = mid + 6;
  }
  for (const e of ends) svg.append(el("text", { x: x(e.p.t) + 6, y: e.ly }, e.label));

  const cross = el("line", { class: "cross", y1: PAD.t, y2: H - PAD.b, visibility: "hidden" });
  const dots = [el("circle", { class: "dot d1", r: 4, visibility: "hidden" }), el("circle", { class: "dot d2", r: 4, visibility: "hidden" })];
  svg.append(cross, ...dots);
  fig.replaceChildren(svg);
  return { svg, x, show(p) {
    const vis = p ? "visible" : "hidden";
    cross.setAttribute("visibility", vis);
    if (p) cross.setAttribute("x1", x(p.t)), cross.setAttribute("x2", x(p.t));
    [p?.lo, p?.hi].forEach((lv, i) => {
      dots[i].setAttribute("visibility", p && lv ? "visible" : "hidden");
      if (p && lv) dots[i].setAttribute("cx", x(p.t)), dots[i].setAttribute("cy", y(lv[key]));
    });
  } };
}

function statusStrip(fig, x) {
  const H = 34;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Spray status over time" });
  for (const p of points) {
    const w = Math.max(2, x(p.t + 300_000) - x(p.t) - 1);
    svg.append(el("rect", { class: p.status, x: x(p.t), y: 4, width: w, height: H - 12, rx: 2 }));
  }
  const cross = el("line", { class: "cross", y1: 0, y2: H, visibility: "hidden" });
  svg.append(cross);
  fig.replaceChildren(svg);
  return { svg, x, show(p) {
    cross.setAttribute("visibility", p ? "visible" : "hidden");
    if (p) cross.setAttribute("x1", x(p.t)), cross.setAttribute("x2", x(p.t));
  } };
}

function tipText(p) {
  const row = (name, lv) => lv ? `${name}: ${fmt(lv.temp_f, "°F")}, ${fmt(lv.wind_mph, " mph")} ${lv.wind_dir_deg != null ? compass(lv.wind_dir_deg) : ""}` : `${name}: no data`;
  const flags = p.checks.length ? ` (${p.checks.map((c) => c.replace(/_/g, " ")).join(", ")})` : "";
  return [clock(p.t), row("30 ft", p.hi), row("5 ft", p.lo), `${p.status}${flags}`];
}

function hover(charts) {
  const tip = $("tip");
  const nearest = (t) => points.reduce((a, b) => Math.abs(b.t - t) < Math.abs(a.t - t) ? b : a);
  const hide = () => { charts.forEach((c) => c.show(null)); tip.hidden = true; };
  for (const c of charts) {
    c.svg.addEventListener("pointermove", (ev) => {
      const box = c.svg.getBoundingClientRect();
      const vx = ((ev.clientX - box.left) / box.width) * W;
      const p = nearest(c.x.invert(vx));
      charts.forEach((k) => k.show(p));
      tip.replaceChildren(...tipText(p).map((s, i) => Object.assign(document.createElement("div"), { textContent: s, className: i ? "" : "muted" })));
      tip.hidden = false;
      const left = Math.min(ev.clientX + 12, window.innerWidth - tip.offsetWidth - 8);
      tip.style.left = `${Math.max(8, left)}px`;
      tip.style.top = `${ev.clientY + 14}px`;
    });
    c.svg.addEventListener("pointerleave", hide);
  }
}

function renderNow(latest, ageS) {
  $("now-section").hidden = false;
  const levels = [...latest.levels].reverse();
  $("now").replaceChildren(...levels.map((lv) => {
    const tr = document.createElement("tr");
    tr.append(td(`${lv.height_ft} ft`), td(fmt(lv.temp_f, "°F")), td(fmt(lv.wind_mph, " mph")), td(compass(lv.wind_dir_deg)));
    return tr;
  }));
  const p = toPoint(latest);
  const parts = [];
  if (p.lo && p.hi) {
    const dt = p.hi.temp_f - p.lo.temp_f;
    parts.push(dt > 0 ? `Inversion: 30 ft is ${dt.toFixed(1)}°F warmer than 5 ft.` : `No inversion: 30 ft is ${(-dt).toFixed(1)}°F cooler than 5 ft.`);
  }
  parts.push(`Status with a generic label: ${latest.status}.`);
  $("now-summary").textContent = parts.join(" ");
  const mins = Math.round(ageS / 60);
  $("station-warn").hidden = mins <= 15;
  $("station-warn").textContent = `No new report for ${mins} minutes. The station may be offline or its sensors may be reporting missing data.`;
}

function renderTable() {
  $("table").replaceChildren(...[...points].reverse().map((p) => {
    const tr = document.createElement("tr");
    const lv = (l) => l ? `${fmt(l.temp_f, "°F")} · ${fmt(l.wind_mph, " mph")}` : "–";
    tr.append(td(clock(p.t)), td(lv(p.lo)), td(lv(p.hi)), td(p.status));
    return tr;
  }));
}

async function load() {
  let data;
  try {
    data = await (await fetch("/api/station")).json();
  } catch {
    $("station-meta").textContent = "Couldn't reach the app. Check your connection.";
    return;
  }
  if (!data.latest) {
    $("station-meta").textContent = {
      push: "No reports from the farm station yet.",
      mesonet: "No usable readings from the station right now (its data file may be missing, or every recent reading is incomplete).",
    }[data.weather] ?? "This server isn't listening to a farm station (start it with FARM_WEATHER=mesonet or push).";
    return;
  }
  points = data.history.map(toPoint);
  const shift = data.replay_shift_h ? ` · replaying recorded Oklahoma Mesonet data, shifted ${data.replay_shift_h} h` : "";
  $("station-meta").textContent = `${data.latest.source} · last report ${clock(data.latest.timestamp)} · ${points.length} reports${shift}`;
  renderNow(data.latest, data.age_s);
  $("charts").hidden = false;
  const temp = lineChart($("chart-temp"), "temp_f", "Temperature", [
    { cls: "band", when: (p) => p.lo && p.hi && p.hi.temp_f > p.lo.temp_f },
  ]);
  const wind = lineChart($("chart-wind"), "wind_mph", "Wind speed", [{ cls: "ok-band", y: [3, 10] }]);
  hover([temp, wind, statusStrip($("chart-status"), temp.x)]);
  renderTable();
}

load();
setInterval(load, REFRESH_MS);
