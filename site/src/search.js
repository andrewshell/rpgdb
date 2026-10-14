// Same normalisation as norm() in books.py: lowercase, punctuation to spaces, drop filler words.
const STOP = new Set(["the", "a", "an", "of"]);
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w && !STOP.has(w));

const q = document.getElementById("q");
const status = document.getElementById("status");
const items = [...document.querySelectorAll("#list li")].map((li) => ({ li, hay: norm(li.dataset.search).join(" ") }));

q.addEventListener("input", () => {
  const words = norm(q.value);
  let shown = 0;
  for (const { li, hay } of items) {
    li.hidden = !words.every((w) => hay.includes(w));
    if (!li.hidden) shown++;
  }
  status.className = words.length && shown ? "hit" : "";
  status.textContent = !words.length
    ? `${items.length} books`
    : shown
      ? `Owned: ${shown} match${shown > 1 ? "es" : ""}`
      : "Not in your collection";
});
