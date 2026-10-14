// Same normalisation as norm() in books.py: lowercase, punctuation to spaces, drop filler words.
const STOP = new Set(["the", "a", "an", "of"]);
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w && !STOP.has(w));

const q = document.getElementById("q");
const status = document.getElementById("status");
const items = [...document.querySelectorAll("#list li")].map((li) => ({ li, hay: norm(li.dataset.search).join(" ") }));

// Offline support: sw.js caches the page and thumbnails; large covers are fetched here in the
// background so they're available offline too.
const offline = document.getElementById("offline");
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").then(() => navigator.serviceWorker.ready).then(cacheLargeCovers, () => {});
}

async function cacheLargeCovers() {
  const urls = [...document.querySelectorAll("a.cover")].map((a) => a.href);
  const cache = await caches.open("shelf-large");
  let missing = 0;
  for (const url of urls) if (!(await cache.match(url))) missing++;
  if (!missing) {
    offline.textContent = "Available offline";
    return;
  }
  let done = urls.length - missing;
  for (const url of urls) {
    if (await cache.match(url)) continue;
    offline.textContent = `Saving covers for offline use… ${done}/${urls.length}`;
    try {
      const response = await fetch(url);
      if (response.ok) await cache.put(url, response);
    } catch {
      offline.textContent = "Offline; covers will finish saving when you're back online";
      return;
    }
    done++;
  }
  offline.textContent = "Available offline";
}

const viewer = document.getElementById("viewer");
const viewerImg = viewer.querySelector("img");
const viewerCaption = viewer.querySelector("p");

document.getElementById("list").addEventListener("click", (e) => {
  const link = e.target.closest("a.cover");
  if (!link) return;
  e.preventDefault();
  viewerImg.src = link.href;
  viewerImg.alt = link.querySelector("img").alt;
  viewerCaption.textContent = link.closest("li").querySelector("a:not(.cover), strong").textContent;
  viewer.showModal();
});
viewer.addEventListener("click", () => viewer.close());
viewer.addEventListener("close", () => viewerImg.removeAttribute("src"));

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
