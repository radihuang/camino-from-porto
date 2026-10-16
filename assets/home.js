(async () => {
  const data = await loadSite();
  const { site } = data;
  document.getElementById("title").textContent = site.title;
  document.getElementById("subtitle").textContent = site.subtitle;
  document.getElementById("intro").textContent = site.intro;

  const walk = site.stages.filter((s) => s.mode === "walk");
  const km = walk.reduce((n, s) => n + s.km, 0);
  const steps = site.stages.reduce((n, s) => n + (s.steps || 0), 0);
  const totals = document.getElementById("totals");
  for (const [v, l] of [[walk.length, "步行天數"], [`${Math.round(km)}`, "公里"], [steps.toLocaleString("en-US"), "步"], [site.stages.filter((s) => s.ready).length, "已整理"]]) {
    const d = document.createElement("div");
    const b = document.createElement("b");
    b.textContent = v;
    const span = document.createElement("span");
    span.textContent = l;
    d.append(b, span);
    totals.append(d);
  }

  const list = document.getElementById("list");
  const items = {};
  for (const s of site.stages) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `stage.html?s=${s.id}`;
    const lbl = document.createElement("span");
    lbl.className = "lbl";
    lbl.textContent = s.label;
    const ttl = document.createElement("span");
    ttl.className = "ttl";
    ttl.textContent = s.title;
    const small = document.createElement("small");
    small.textContent = fmtDate(s);
    if (!s.ready) {
      const b = document.createElement("span");
      b.className = "badge";
      b.textContent = "整理中";
      small.append(b);
    }
    ttl.append(small);
    const k = document.createElement("span");
    k.className = "km";
    k.textContent = fmtKm(s);
    if (s.steps) {
      const st = document.createElement("small");
      st.textContent = fmtSteps(s.steps);
      k.append(st);
    }
    a.append(lbl, ttl, k);
    li.append(a);
    list.append(li);
    items[s.id] = a;
  }

  const mapEl = document.getElementById("map");
  const map = drawMap(mapEl, data, {
    onHover(id) {
      for (const [sid, a] of Object.entries(items)) a.classList.toggle("is-on", sid === id);
    },
  });
  mapEl.removeAttribute("aria-busy");
  for (const [id, a] of Object.entries(items)) {
    a.addEventListener("mouseenter", () => map.highlight(id));
    a.addEventListener("mouseleave", () => map.highlight(null));
  }
})();
