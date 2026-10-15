import json
import shutil
from pathlib import Path

from scripts.check_content import ROOT, check


def test_real_content_passes():
    problems, _ = check(ROOT)
    assert problems == []


def make_site(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    (tmp_path / "stages").mkdir()
    (tmp_path / "photos" / "day01").mkdir(parents=True)
    (tmp_path / "photos" / "day01" / "ok.jpg").write_bytes(b"x")
    return tmp_path


def test_catches_missing_photo_and_bad_video(tmp_path):
    root = make_site(tmp_path)
    (root / "stages" / "day01.md").write_text(
        "```gallery\nday01/ok.jpg | 有\nday01/missing.jpg | 沒有\n```\n"
        "```youtube\nnot-a-valid-id | x\n```\n"
        "```video\nday01/nope.mp4 | x\n```\n", encoding="utf-8")
    problems, photos = check(root)
    assert photos == 2
    assert any("missing.jpg" in p for p in problems)
    assert not any("ok.jpg" in p for p in problems)
    assert any("影片 ID" in p for p in problems)
    assert any("nope.mp4" in p for p in problems)


def test_catches_ready_without_markdown_and_unknown_stop(tmp_path):
    root = make_site(tmp_path)
    path = root / "data" / "stages.json"
    site = json.loads(path.read_text(encoding="utf-8"))
    site["stages"][2]["stop"] = "nowhere"
    path.write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
    problems, _ = check(root)  # day01 標 ready 但這個暫存站沒有 day01.md
    assert any("day01" in p and "ready" in p for p in problems)
    assert any("nowhere" in p for p in problems)
