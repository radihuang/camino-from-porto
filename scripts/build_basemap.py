"""從 Natural Earth 10m 資料產生手繪地圖底圖 data/basemap.json。

用法：
    uv run scripts/build_basemap.py <natural-earth-geojson 資料夾>

資料夾內需有 ne_10m_land / ne_10m_coastline / ne_10m_admin_0_boundary_lines_land /
ne_10m_rivers_lake_centerlines 四個 .geojson（github.com/nvkelso/natural-earth-vector）。
底圖只需要產生一次，產物已進版控；只有改地圖範圍時才要重跑。
"""

import json
import math
import sys
from pathlib import Path

# 地圖範圍：涵蓋 Porto 到 Muxía／Fisterra
LON_MIN, LON_MAX = -9.45, -8.0
LAT_MIN, LAT_MAX = 41.05, 43.25
SCALE = 500  # 每 1 度緯度的 viewBox 單位
COS = math.cos(math.radians((LAT_MIN + LAT_MAX) / 2))
SIMPLIFY = 0.8  # viewBox 單位

OUT = Path(__file__).resolve().parent.parent / "data" / "basemap.json"


def project(lon, lat):
    return ((lon - LON_MIN) * COS * SCALE, (LAT_MAX - lat) * SCALE)


def clip_ring(ring):
    """Sutherland–Hodgman，把多邊形環裁到地圖範圍（矩形是凸的，可以直接用）。"""
    edges = [
        lambda p: p[0] >= LON_MIN, lambda p: p[0] <= LON_MAX,
        lambda p: p[1] >= LAT_MIN, lambda p: p[1] <= LAT_MAX,
    ]
    bounds = [("x", LON_MIN), ("x", LON_MAX), ("y", LAT_MIN), ("y", LAT_MAX)]
    pts = ring
    for inside, (axis, v) in zip(edges, bounds):
        if not pts:
            break
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(intersect(prev, cur, axis, v))
                out.append(cur)
            elif inside(prev):
                out.append(intersect(prev, cur, axis, v))
        pts = out
    return pts


def intersect(a, b, axis, v):
    if axis == "x":
        t = (v - a[0]) / (b[0] - a[0])
        return (v, a[1] + t * (b[1] - a[1]))
    t = (v - a[1]) / (b[1] - a[1])
    return (a[0] + t * (b[0] - a[0]), v)


def clip_line(line):
    """折線只保留落在範圍內的連續片段（端點略出界沒關係，SVG 會裁掉）。"""
    pad = 0.05
    segs, cur = [], []
    for x, y in line:
        if LON_MIN - pad <= x <= LON_MAX + pad and LAT_MIN - pad <= y <= LAT_MAX + pad:
            cur.append((x, y))
        elif cur:
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    return [s for s in segs if len(s) > 1]


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def to_path(pts, closed):
    xy = rdp([project(*p) for p in pts], SIMPLIFY)
    if len(xy) < 2:
        return ""
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    return d + ("Z" if closed else "")


def lines_of(geom):
    t, c = geom["type"], geom["coordinates"]
    return [c] if t == "LineString" else c if t == "MultiLineString" else []


def rings_of(geom):
    t, c = geom["type"], geom["coordinates"]
    polys = [c] if t == "Polygon" else c if t == "MultiPolygon" else []
    return [ring for poly in polys for ring in poly]


def main(src):
    src = Path(src)
    load = lambda name: json.loads((src / f"{name}.geojson").read_text(encoding="utf-8"))

    land = []
    for f in load("ne_10m_land")["features"]:
        for ring in rings_of(f["geometry"]):
            clipped = clip_ring([tuple(p) for p in ring])
            if len(clipped) > 2:
                land.append(to_path(clipped, True))

    # 海岸線另外用 coastline 資料畫，land 只負責填色；否則裁切邊也會被描成海岸
    coast = []
    for f in load("ne_10m_coastline")["features"]:
        for line in lines_of(f["geometry"]):
            coast += [to_path(s, False) for s in clip_line(line)]

    border = []
    for f in load("ne_10m_admin_0_boundary_lines_land")["features"]:
        for line in lines_of(f["geometry"]):
            border += [to_path(s, False) for s in clip_line(line)]

    rivers = []
    for f in load("ne_10m_rivers_lake_centerlines")["features"]:
        for line in lines_of(f["geometry"]):
            rivers += [to_path(s, False) for s in clip_line(line)]

    w, h = project(LON_MAX, LAT_MIN)
    out = {
        "projection": {"lonMin": LON_MIN, "latMax": LAT_MAX, "cos": COS, "scale": SCALE},
        "width": round(w, 1),
        "height": round(h, 1),
        "land": [p for p in land if p],
        "coast": [p for p in coast if p],
        "border": [p for p in border if p],
        "rivers": [p for p in rivers if p],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"land {len(out['land'])} / coast {len(out['coast'])} / border {len(out['border'])} / rivers {len(out['rivers'])}"
          f" paths, {OUT.stat().st_size // 1024} KB, viewBox {out['width']}x{out['height']}")


if __name__ == "__main__":
    main(sys.argv[1])
