"""檢查內容是否一致：push 前跑一次 `uv run python scripts/check_content.py`。

會抓的問題：stages.json 格式錯、站點不存在、標了 ready 卻沒有 .md、
.md 裡引用的照片檔不存在、影片 ID 格式錯。
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCK_RE = re.compile(r"^```(gallery|video|youtube)[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


def check(root: Path) -> tuple[list[str], int]:
    """回傳 (問題清單, 檢查過的照片數)。"""
    problems = []
    site = json.loads((root / "data" / "stages.json").read_text(encoding="utf-8"))
    places = site["places"]
    seen = set()
    photos = 0
    for s in site["stages"]:
        sid = s["id"]
        if sid in seen:
            problems.append(f"{sid}: id 重複")
        seen.add(sid)
        if s["stop"] not in places:
            problems.append(f"{sid}: 站點 {s['stop']} 不在 places 裡")
        if "steps" in s and not (isinstance(s["steps"], int) and s["steps"] > 0):
            problems.append(f"{sid}: steps 要是正整數")
        if s["mode"] not in {"walk", "stay", "bus"}:
            problems.append(f"{sid}: mode 只能是 walk/stay/bus")
        md = root / "stages" / f"{sid}.md"
        if s.get("ready") and not md.exists():
            problems.append(f"{sid}: 標了 ready 但沒有 stages/{sid}.md")
        if not md.exists():
            continue
        for kind, body in BLOCK_RE.findall(md.read_text(encoding="utf-8")):
            for line in filter(str.strip, body.splitlines()):
                ref = line.split("|")[0].strip()
                if kind == "gallery":
                    photos += 1
                    if ".." in ref or not (root / "photos" / ref).is_file():
                        problems.append(f"{sid}: 找不到照片 photos/{ref}")
                elif kind == "video":
                    if ".." in ref or not (root / "videos" / ref).is_file():
                        problems.append(f"{sid}: 找不到影片 videos/{ref}")
                elif not re.fullmatch(r"[\w-]{11}", ref):
                    problems.append(f"{sid}: 影片 ID 格式不對：{ref}")
    return problems, photos


if __name__ == "__main__":
    problems, photos = check(ROOT)
    for p in problems:
        print("✗", p)
    print(f"檢查 {len(json.loads((ROOT / 'data/stages.json').read_text(encoding='utf-8'))['stages'])} 段、{photos} 張照片引用，{len(problems)} 個問題")
    sys.exit(1 if problems else 0)
