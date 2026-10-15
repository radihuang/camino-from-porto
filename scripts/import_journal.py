"""從 Heptabase 的日記擷取某一段路當天的內容（只讀，不會改 Heptabase）。

用法：
    uv run python scripts/import_journal.py day04

- 日期取自 data/stages.json 的 date
- 排除所有待辦項目：每天固定的「肯定／感恩／學習／故事」checklist，以及夾在日記裡的私人待辦
- 印出純文字段落，空行去掉；內容是語音輸入原文，貼進 .md 前要人工整理錯字、刪掉不公開的內容
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = os.environ.get("HEPTA_DB", str(Path.home() / "Library/Application Support/project-meta/hepta.db"))


def text_of(node):
    if node.get("type") == "text":
        return node.get("text", "")
    if node.get("type") == "hard_break":
        return "\n"
    return "".join(text_of(c) for c in node.get("content", []))


def journal_paragraphs(content_json):
    doc = json.loads(content_json)
    paras = [text_of(n).strip() for n in doc.get("content", []) if n.get("type") != "todo_list_item"]
    return [p for p in paras if p]


def main(stage_id):
    site = json.loads((ROOT / "data" / "stages.json").read_text(encoding="utf-8"))
    stage = next((s for s in site["stages"] if s["id"] == stage_id), None)
    if not stage:
        sys.exit(f"stages.json 裡沒有 {stage_id}")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    row = con.execute("SELECT content FROM journal WHERE date = ?", (stage["date"],)).fetchone()
    if not row:
        sys.exit(f"Heptabase 沒有 {stage['date']} 的日記")
    paras = journal_paragraphs(row[0])
    print(f"# {stage_id}（{stage['date']}）{len(paras)} 段")
    print("\n".join(paras) if paras else "（這天只有模板，沒有寫內容）")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
