"""從 OpenStreetMap 的朝聖之路路線產生每段的實際路徑 data/routes.json。

用法：
    uv run python scripts/build_routes.py <overpass 匯出的 ways.json>

ways.json 用 Overpass API 取得（只抓實際走過的路線，避免最短路徑抄到其他變體）：
    [out:json];(relation(id:6100606,12786089,12786090,6102927,17600329,18091699);>>;);way._;out geom;
  6100606 / 17600329 / 18091699  海岸線（Porto → Vila do Conde）
  6102927                        海岸線與中央線的連接段 CP Costa - CP Central（Vila do Conde → Rates）
  12786089 / 12786090            中央線（→ Santiago）

做法：把所有路段建成路網，每段從起點站到終點站跑最短路徑（Dijkstra）。
算出的長度會跟 stages.json 的計畫公里數比對，差太多就代表接錯路，要人工檢查。
路線資料 © OpenStreetMap contributors（ODbL）。
"""

import heapq
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "routes.json"

# 中途必經的站（其餘段落就是前一站 → 本站）
LEGS = {"day02": ["labruge", "vilaconde", "rates"]}

# OSM 沒畫到的部分，用沿途地標手動補：Porto 市區沿杜羅河到 Foz，再沿海到 Matosinhos。
# 每段開頭先走這些點，最後一點接回路網。
MANUAL_PREFIX = {
    "day01": [
        (41.1428, -8.6112),  # Sé
        (41.1405, -8.6132),  # Ribeira
        (41.1432, -8.6240),  # Miragaia
        (41.1476, -8.6403),  # Ponte da Arrábida
        (41.1468, -8.6650),  # Cantareira
        (41.1495, -8.6770),  # Farol de Felgueiras
        (41.1580, -8.6835),
        (41.1660, -8.6905),  # Castelo do Queijo
        (41.1800, -8.6920),  # Matosinhos
        (41.1875, -8.6928),
    ],
}
SNAP_WARN_M = 1500
JOIN_M = 60  # 不同人畫的路段在交會處常沒共用節點，端點距離這麼近就視為相連
KM_TOLERANCE = 0.2  # 跟計畫公里數差超過 20% 就標警告


def dist_m(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def build_graph(ways):
    coords, adj = {}, {}
    for w in ways:
        ids, geom = w["nodes"], w["geometry"]
        for nid, g in zip(ids, geom):
            coords[nid] = (g["lat"], g["lon"])
        for a, b in zip(ids, ids[1:]):
            d = dist_m(coords[a], coords[b])
            adj.setdefault(a, []).append((b, d))
            adj.setdefault(b, []).append((a, d))
    joined = join_endpoints(ways, coords, adj)
    return coords, adj, joined


def join_endpoints(ways, coords, adj):
    """把每條路段的端點接到 JOIN_M 內最近的其他節點（用網格加速）。"""
    cell = 0.001  # 約 100 m
    grid = {}
    for nid, (la, lo) in coords.items():
        grid.setdefault((int(la / cell), int(lo / cell)), []).append(nid)
    ends = {w["nodes"][0] for w in ways} | {w["nodes"][-1] for w in ways}
    joined = 0
    for e in ends:
        la, lo = coords[e]
        gx, gy = int(la / cell), int(lo / cell)
        linked = {m for m, _ in adj.get(e, [])}
        best, bd = None, JOIN_M
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for n in grid.get((gx + dx, gy + dy), []):
                    if n == e or n in linked:
                        continue
                    d = dist_m(coords[e], coords[n])
                    if d < bd:
                        best, bd = n, d
        if best is not None:
            adj[e].append((best, bd))
            adj.setdefault(best, []).append((e, bd))
            joined += 1
    return joined


def nearest(coords, p):
    nid = min(coords, key=lambda n: dist_m(coords[n], p))
    return nid, dist_m(coords[nid], p)


def shortest(adj, src, dst):
    best, prev = {src: 0.0}, {}
    pq = [(0.0, src)]
    while pq:
        d, n = heapq.heappop(pq)
        if n == dst:
            break
        if d > best[n]:
            continue
        for m, w in adj.get(n, []):
            nd = d + w
            if nd < best.get(m, math.inf):
                best[m], prev[m] = nd, n
                heapq.heappush(pq, (nd, m))
    if dst not in best:
        return None, None
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path[::-1], best[dst]


def simplify(pts, eps_m=12):
    """RDP，在公尺尺度上簡化，地圖上看不出差別但檔案小很多。"""
    if len(pts) < 3:
        return pts
    k = math.cos(math.radians(pts[0][0]))
    xy = [(p[1] * 111320 * k, p[0] * 110540) for p in pts]

    def rec(i, j):
        (x1, y1), (x2, y2) = xy[i], xy[j]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1e-9
        far, fi = 0, i
        for t in range(i + 1, j):
            d = abs(dy * xy[t][0] - dx * xy[t][1] + x2 * y1 - y2 * x1) / n
            if d > far:
                far, fi = d, t
        return rec(i, fi)[:-1] + rec(fi, j) if far > eps_m else [i, j]

    return [pts[i] for i in rec(0, len(pts) - 1)]


def main(ways_path):
    data = json.loads(Path(ways_path).read_text(encoding="utf-8"))
    ways = [e for e in data["elements"] if e["type"] == "way"]
    coords, adj, joined = build_graph(ways)
    site = json.loads((ROOT / "data" / "stages.json").read_text(encoding="utf-8"))
    places = site["places"]
    print(f"路網：{len(ways)} 條路段、{len(coords)} 個節點，補接 {joined} 處端點")

    routes, warnings, prev_stop, snaps = {}, [], None, {}
    for s in site["stages"]:
        stops = LEGS.get(s["id"], [prev_stop, s["stop"]])
        prev_stop = s["stop"]
        if s["mode"] != "walk":
            continue
        line, total = [], 0.0
        manual = MANUAL_PREFIX.get(s["id"])
        if manual:
            line = list(manual)
            total = sum(dist_m(p, q) for p, q in zip(manual, manual[1:]))
        for a, b in zip(stops, stops[1:]):
            start = manual[-1] if manual and a == stops[0] else (places[a]["lat"], places[a]["lon"])
            na, da = nearest(coords, start)
            nb, db = nearest(coords, (places[b]["lat"], places[b]["lon"]))
            for name, d in ((a, da), (b, db)):
                snaps[name] = d
                if d > SNAP_WARN_M:
                    warnings.append(f"{s['id']}: {name} 離路網 {d:.0f} m")
            path, length = shortest(adj, na, nb)
            if path is None:
                warnings.append(f"{s['id']}: {a} → {b} 在路網上不相通")
                line = None
                break
            line += [coords[n] for n in path]
            total += length
        if not line:
            continue
        km = total / 1000
        diff = (km - s["km"]) / s["km"]
        flag = "" if abs(diff) <= KM_TOLERANCE else "  ← 差太多，要檢查"
        if flag:
            warnings.append(f"{s['id']}: 算出 {km:.1f} km，計畫 {s['km']} km")
        print(f"{s['id']}: {km:5.1f} km（計畫 {s['km']:>4} km，{diff:+.0%}）{flag}")
        routes[s["id"]] = {"km": round(km, 1),
                           "path": [[round(la, 5), round(lo, 5)] for la, lo in simplify(line)]}

    OUT.write_text(json.dumps({"source": "© OpenStreetMap contributors (ODbL)", "routes": routes},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"寫出 {len(routes)} 段，{OUT.stat().st_size // 1024} KB")
    print("各站離路網：" + "、".join(f"{k} {v:.0f}m" for k, v in snaps.items()))
    for w in warnings:
        print("⚠", w)


if __name__ == "__main__":
    main(sys.argv[1])
