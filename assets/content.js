// 把路段的 Markdown 轉成頁面。除了一般 Markdown，另外認三種區塊：
//   ```gallery   每行一張：day01/IMG_1234.jpg | 說明
//   ```video     每行一支短片：day01/IMG_4467.mp4 | 說明（放在 videos/ 底下）
//   ```youtube   每行一支：影片ID | 說明
//   ```qa        第一行 Q: 問題；可加一行「狀態: 已查證」；其餘是答案（可用 Markdown）
const BLOCK_RE = /^```(gallery|video|youtube|qa)[ \t]*\n([\s\S]*?)^```[ \t]*$/gm;

function md(text) {
  return DOMPurify.sanitize(marked.parse(text));
}

function renderContent(target, source, onPhoto) {
  const blocks = [];
  const replaced = source.replace(BLOCK_RE, (_, kind, body) => {
    blocks.push({ kind, body });
    return `\n<div data-block="${blocks.length - 1}"></div>\n`;
  });
  target.innerHTML = md(replaced);
  target.querySelectorAll("[data-block]").forEach((holder) => {
    const b = blocks[Number(holder.dataset.block)];
    const node = { gallery: buildGallery, video: buildClips, youtube: buildVideos, qa: buildQA }[b.kind](b.body, onPhoto);
    holder.replaceWith(node);
  });
}

function splitLine(line) {
  const i = line.indexOf("|");
  return i < 0 ? [line.trim(), ""] : [line.slice(0, i).trim(), line.slice(i + 1).trim()];
}

const SAFE_PATH = /^[\w\-]+(\/[\w\-.]+)+$/;

function buildGallery(body, onPhoto) {
  const wrap = document.createElement("div");
  wrap.className = "gallery";
  const photos = [];
  for (const line of body.split("\n").filter((l) => l.trim())) {
    const [path, cap] = splitLine(line);
    if (!SAFE_PATH.test(path) || path.includes("..")) continue;
    const full = `photos/${path}`;
    const thumb = full.replace(/\/([^/]+)$/, "/thumbs/$1");
    const idx = photos.push({ src: full, cap }) - 1;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("aria-label", cap || "放大照片");
    const img = document.createElement("img");
    img.loading = "lazy";
    img.alt = cap;
    img.src = thumb;
    img.addEventListener("error", () => { if (img.src.endsWith(thumb)) img.src = full; }, { once: true });
    btn.append(img);
    btn.addEventListener("click", () => onPhoto(photos, idx));
    wrap.append(btn);
  }
  return wrap;
}

function buildClips(body) {
  const wrap = document.createElement("div");
  wrap.className = "clips";
  for (const line of body.split("\n").filter((l) => l.trim())) {
    const [path, cap] = splitLine(line);
    if (!SAFE_PATH.test(path) || path.includes("..")) continue;
    const fig = document.createElement("figure");
    const v = document.createElement("video");
    v.src = `videos/${path}`;
    v.poster = `videos/${path.replace(/\.mp4$/, ".jpg")}`;
    v.controls = true;
    v.playsInline = true;
    v.preload = "none";
    fig.append(v);
    if (cap) {
      const c = document.createElement("figcaption");
      c.textContent = cap;
      fig.append(c);
    }
    wrap.append(fig);
  }
  return wrap;
}

function buildVideos(body) {
  const frag = document.createDocumentFragment();
  for (const line of body.split("\n").filter((l) => l.trim())) {
    const [id, cap] = splitLine(line);
    if (!/^[\w-]{11}$/.test(id)) continue;
    const box = document.createElement("div");
    box.className = "video";
    const f = document.createElement("iframe");
    f.src = `https://www.youtube-nocookie.com/embed/${id}`;
    f.title = cap || "影片";
    f.loading = "lazy";
    f.allow = "encrypted-media; picture-in-picture; fullscreen";
    f.allowFullscreen = true;
    box.append(f);
    frag.append(box);
    if (cap) {
      const p = document.createElement("p");
      p.className = "video-cap";
      p.textContent = cap;
      frag.append(p);
    }
  }
  return frag;
}

function buildQA(body) {
  const lines = body.split("\n");
  let q = "", status = "未查證";
  const rest = [];
  for (const line of lines) {
    const mq = line.match(/^Q[:：]\s*(.+)$/);
    const ms = line.match(/^狀態[:：]\s*(.+)$/);
    if (mq && !q) q = mq[1].trim();
    else if (ms && !rest.length) status = ms[1].trim();
    else rest.push(line);
  }
  const d = document.createElement("details");
  d.className = "qa";
  const s = document.createElement("summary");
  const qs = document.createElement("span");
  qs.className = "q";
  qs.textContent = q;
  const st = document.createElement("span");
  st.className = "status " + (status === "已查證" ? "status--ok" : "status--todo");
  st.textContent = status;
  s.append(qs, st);
  const a = document.createElement("div");
  a.className = "answer";
  a.innerHTML = md(rest.join("\n").trim());
  d.append(s, a);
  return d;
}
