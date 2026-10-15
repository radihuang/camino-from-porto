(async () => {
  const data = await loadSite();
  const { site } = data;
  const id = new URLSearchParams(location.search).get("s");
  const stage = site.stages.find((s) => s.id === id);
  const content = document.getElementById("content");

  if (!stage) {
    document.getElementById("title").textContent = "找不到這一段";
    content.innerHTML = '<p><a href="./">回到地圖</a></p>';
    return;
  }

  document.title = `${stage.label} ${stage.title}｜葡萄牙之路`;
  document.getElementById("lbl").textContent = stage.label;
  document.getElementById("title").textContent = stage.title;
  document.getElementById("meta").textContent = `2026/${fmtDate(stage)}　·　${fmtKm(stage)}`;
  document.getElementById("pos").textContent = `${stage.index + 1} / ${site.stages.length}`;
  drawMap(document.getElementById("map"), data, { focus: stage.id });

  if (stage.ready) {
    try {
      const r = await fetch(`stages/${stage.id}.md`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      renderContent(content, await r.text(), openLightbox);
    } catch (e) {
      content.innerHTML = "";
      const p = document.createElement("p");
      p.className = "empty";
      p.textContent = `內容載入失敗（stages/${stage.id}.md：${e.message}）`;
      content.append(p);
    }
  } else {
    content.innerHTML = '<p class="empty">這一段還在整理中，之後會補上照片和故事。</p>';
  }

  const pager = document.getElementById("pager");
  const prev = site.stages[stage.index - 1], next = site.stages[stage.index + 1];
  for (const [s, cls, hint] of [[prev, "prev", "← 上一段"], [next, "next", "下一段 →"]]) {
    if (!s) continue;
    const a = document.createElement("a");
    a.className = cls;
    a.href = `stage.html?s=${s.id}`;
    const small = document.createElement("small");
    small.textContent = hint;
    a.append(small, `${s.label}　${s.title}`);
    pager.append(a);
  }

  // 燈箱
  const lb = document.getElementById("lightbox");
  const img = document.getElementById("lb-img"), cap = document.getElementById("lb-cap");
  let list = [], cur = 0;
  function show(i) {
    cur = (i + list.length) % list.length;
    img.src = list[cur].src;
    img.alt = list[cur].cap;
    cap.textContent = list[cur].cap;
  }
  function openLightbox(photos, i) { list = photos; show(i); lb.hidden = false; document.getElementById("lb-close").focus(); }
  function close() { lb.hidden = true; img.removeAttribute("src"); }
  document.getElementById("lb-close").onclick = close;
  document.getElementById("lb-prev").onclick = () => show(cur - 1);
  document.getElementById("lb-next").onclick = () => show(cur + 1);
  lb.addEventListener("click", (e) => { if (e.target === lb) close(); });
  document.addEventListener("keydown", (e) => {
    if (lb.hidden) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(cur - 1);
    if (e.key === "ArrowRight") show(cur + 1);
  });
})();
