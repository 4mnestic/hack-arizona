// Shows how many entries each log has, so you know the download isn't empty.
for (const mode of ["live", "demo"]) {
  fetch(`/api/log?mode=${mode}&limit=0`)
    .then((r) => r.json())
    .then((items) => {
      const last = items[0] && new Date(items[0].reading.timestamp)
        .toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
      document.getElementById(`${mode}-info`).textContent =
        items.length ? `${items.length} ${items.length === 1 ? "entry" : "entries"} · latest ${last}` : "No entries yet";
    })
    .catch(() => {});
}

// Latest live entries: time, pesticide, status, and the checks that triggered it. Status changes are bold.
function row(e) {
  const tr = document.createElement("tr");
  if (e.changed_from) tr.className = "changed";
  const when = new Date(e.reading.timestamp).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const status = e.changed_from ? `${e.changed_from} → ${e.decision.status}` : e.decision.status;
  const checks = [...new Set(e.decision.flags.map((f) => f.check.replace(/_/g, " ")))].join(", ") || "none";
  for (const text of [when, e.pesticide, status, checks]) {
    const td = document.createElement("td");
    td.textContent = text;
    tr.append(td);
  }
  return tr;
}

function loadRecent() {
  fetch("/api/log?mode=live&limit=50")
    .then((r) => r.json())
    .then((items) => {
      document.getElementById("entries").replaceChildren(...items.map(row));
      document.getElementById("empty").hidden = items.length > 0;
    })
    .catch(() => {});
}

loadRecent();
setInterval(loadRecent, 60_000);
