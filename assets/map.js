// 共用：載入資料、畫手繪地圖
const SVG_NS = "http://www.w3.org/2000/svg";

// 站名標籤放左邊（海上）的站，避免跟路線或鄰站重疊
const LABEL_LEFT = new Set(["labruge", "vilaconde", "porto"]);

async function loadSite() {
  const [site, base] = await Promise.all([
    fetch("data/stages.json").then((r) => r.json()),
    fetch("data/basemap.json").then((r) => r.json()),
  ]);
  site.stages.forEach((s, i) => {
    const prev = site.stages.slice(0, i).reverse().find((p) => p.stop);
    s.from = prev ? prev.stop : null;
    s.index = i;
  });
  return { site, base };
}

function makeProjector(base) {
  const p = base.projection;
  return (lat, lon) => [(lon - p.lonMin) * p.cos * p.scale, (p.latMax - lat) * p.scale];
}

function stagePoints(stage, site) {
  if (stage.via) return stage.via;
  if (!stage.from || stage.from === stage.stop) return null;
  const a = site.places[stage.from], b = site.places[stage.stop];
  return [[a.lat, a.lon], [b.lat, b.lon]];
}

// Catmull-Rom 轉 Bézier，讓路線看起來是手畫的曲線而不是折線
function smoothPath(pts) {
  if (pts.length < 3) return "M" + pts.map((p) => p.join(",")).join("L");
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${p2[0]},${p2[1]}`;
  }
  return d;
}

function el(name, attrs = {}, parent) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

function svgText(parent, x, y, text, attrs) {
  const t = el("text", { x, y, ...attrs }, parent);
  t.textContent = text;
  return t;
}

/**
 * 畫地圖。
 * opts.focus: 聚焦的 stage id（路段頁用），其餘路段變淡、視窗縮放到該段
 * opts.onHover: (stageId|null) => void，首頁用來跟清單互動
 */
function drawMap(container, { site, base }, opts = {}) {
  const proj = makeProjector(base);
  const focus = opts.focus ? site.stages.find((s) => s.id === opts.focus) : null;

  let vb = [0, 0, base.width, base.height];
  if (focus) {
    const pts = (stagePoints(focus, site) || [[site.places[focus.stop].lat, site.places[focus.stop].lon]]).map((p) => proj(...p));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const h = Math.max(Math.max(...ys) - Math.min(...ys), (Math.max(...xs) - Math.min(...xs)) / 1.8, 110) * 1.6;
    const w = h * 1.8;
    vb = [cx - w / 2, cy - h / 2, w, h];
  }
  // u：尺寸係數，讓字和線在螢幕上的大小跟縮放程度無關。
  // 全圖約以 1 單位≈0.75px 顯示，小地圖依實際顯示高度換算成同樣的比例
  const u = focus ? vb[3] / (container.clientHeight || 190) : 1;

  const svg = el("svg", { viewBox: vb.join(" "), class: "map" + (focus ? " map--focus" : ""), role: "img",
    "aria-label": "朝聖路線手繪地圖" });
  const defs = el("defs", {}, svg);
  // 用 userSpaceOnUse：預設依物件邊界框算濾鏡範圍，正南北走向的直線邊界框寬度為 0，會整條消失
  const rough = el("filter", { id: "rough", filterUnits: "userSpaceOnUse", x: vb[0] - 50, y: vb[1] - 50, width: vb[2] + 100, height: vb[3] + 100 }, defs);
  el("feTurbulence", { type: "fractalNoise", baseFrequency: 0.035 / u, numOctaves: 2, seed: 7, result: "n" }, rough);
  el("feDisplacementMap", { in: "SourceGraphic", in2: "n", scale: 4 * u, xChannelSelector: "R", yChannelSelector: "G" }, rough);
  const waves = el("pattern", { id: "waves", width: 26 * u, height: 14 * u, patternUnits: "userSpaceOnUse" }, defs);
  el("path", { d: `M${2 * u},${8 * u} q${3 * u},${-4 * u} ${6 * u},0 t${6 * u},0`, class: "wave" }, waves);

  el("rect", { x: vb[0] - 50, y: vb[1] - 50, width: vb[2] + 100, height: vb[3] + 100, fill: "url(#waves)", class: "sea" }, svg);

  const land = el("g", { filter: "url(#rough)" }, svg);
  base.coast.forEach((d) => el("path", { d, class: "coast-glow", "stroke-width": 14 * u }, land));
  base.land.forEach((d) => el("path", { d, class: "land" }, land));
  base.coast.forEach((d) => el("path", { d, class: "coast", "stroke-width": 1.4 * u }, land));
  base.rivers.forEach((d) => el("path", { d, class: "river", "stroke-width": 1.6 * u }, land));
  base.border.forEach((d) => el("path", { d, class: "border", "stroke-width": 1.2 * u, "stroke-dasharray": `${6 * u} ${4 * u}` }, land));

  if (!focus) {
    const deco = el("g", { class: "deco" }, svg);
    svgText(deco, 470, 880, "PORTUGAL", { class: "region", "font-size": 20, "text-anchor": "middle" });
    svgText(deco, 475, 300, "GALICIA", { class: "region", "font-size": 20, "text-anchor": "middle" });
    svgText(deco, 60, 560, "Oceano Atlântico", { class: "sea-label", "font-size": 26, transform: "rotate(-80 60 560)" });
    svgText(deco, 330, 1010, "Rio Douro", { class: "river-label", "font-size": 15 });
    svgText(deco, 455, 600, "Rio Minho", { class: "river-label", "font-size": 15 });
    // 指北針
    const c = el("g", { transform: "translate(120 960)", class: "compass" }, deco);
    el("circle", { r: 26 }, c);
    el("path", { d: "M0,-34 L7,0 L0,6 L-7,0 Z", class: "needle" }, c);
    el("path", { d: "M0,34 L7,0 L0,-6 L-7,0 Z", class: "needle needle--s" }, c);
    svgText(c, 0, -40, "N", { "text-anchor": "middle", "font-size": 18 });
    // 比例尺：緯度 1 度約 111 km
    const km = base.projection.scale / 111;
    const sb = el("g", { transform: "translate(40 1060)", class: "scalebar" }, deco);
    el("path", { d: `M0,0 h${20 * km} M0,-5 v10 M${10 * km},-4 v8 M${20 * km},-5 v10` }, sb);
    svgText(sb, 0, -10, "0", { "font-size": 14 });
    svgText(sb, 20 * km, -10, "20 km", { "font-size": 14, "text-anchor": "middle" });
  }

  // 路線
  const routes = el("g", { class: "routes" }, svg);
  const segs = {};
  site.stages.forEach((s) => {
    const pts = stagePoints(s, site);
    if (!pts) return;
    const d = smoothPath(pts.map((p) => proj(...p)));
    const a = el("a", { href: `stage.html?s=${s.id}`, class: `seg seg--${s.mode}` + (focus && focus.id !== s.id ? " seg--dim" : "") + (focus && focus.id === s.id ? " seg--on" : ""), "data-id": s.id }, routes);
    const title = el("title", {}, a);
    title.textContent = `${s.label}　${s.title}`;
    el("path", { d, class: "seg-halo", "stroke-width": 7 * u }, a);
    el("path", { d, class: "seg-line", "stroke-width": 3.4 * u, ...(s.mode === "bus" ? { "stroke-dasharray": `${2 * u} ${7 * u}` } : {}), filter: "url(#rough)" }, a);
    el("path", { d, class: "seg-hit", "stroke-width": 22 * u }, a);
    segs[s.id] = a;
  });

  // 站點
  const stops = el("g", { class: "stops" }, svg);
  const used = new Set(site.stages.map((s) => s.stop).concat(site.stages.map((s) => s.from)).filter(Boolean));
  for (const key of used) {
    const p = site.places[key];
    const [x, y] = proj(p.lat, p.lon);
    const g = el("g", { class: "stop" + (key === "santiago" ? " stop--goal" : "") }, stops);
    el("circle", { cx: x, cy: y, r: (key === "santiago" ? 6.5 : 4.2) * u }, g);
    const left = LABEL_LEFT.has(key);
    svgText(g, x + (left ? -9 : 9) * u, y + 5 * u, p.name, { "text-anchor": left ? "end" : "start", "font-size": (key === "santiago" ? 21 : 17) * u, class: "stop-label" });
  }

  if (opts.onHover) {
    for (const [id, a] of Object.entries(segs)) {
      a.addEventListener("mouseenter", () => opts.onHover(id));
      a.addEventListener("mouseleave", () => opts.onHover(null));
      a.addEventListener("focus", () => opts.onHover(id));
      a.addEventListener("blur", () => opts.onHover(null));
    }
  }

  container.replaceChildren(svg);
  return {
    highlight(id) {
      for (const [sid, a] of Object.entries(segs)) a.classList.toggle("seg--on", sid === id);
    },
  };
}

function fmtDate(s) {
  const a = new Date(s.date + "T00:00:00");
  let out = `${a.getMonth() + 1}/${a.getDate()}`;
  if (s.dateEnd) {
    const b = new Date(s.dateEnd + "T00:00:00");
    out += `–${b.getMonth() + 1}/${b.getDate()}`;
  }
  return out;
}

function fmtKm(s) {
  if (s.mode === "bus") return "搭車";
  if (s.mode === "stay") return "停留";
  return `${s.km} km`;
}
