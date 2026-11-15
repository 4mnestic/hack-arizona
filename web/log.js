// Shows how many entries each log has, so you know the download isn't empty.
for (const mode of ["live", "demo"]) {
  fetch(`/api/log?mode=${mode}&limit=0`)
    .then((r) => r.json())
    .then((items) => {
      const last = items[0] && new Date(items[0].reading.timestamp)
        .toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
      document.getElementById(`${mode}-info`).textContent =
        items.length ? `${items.length} entries · latest ${last}` : "No entries yet";
    })
    .catch(() => {});
}
