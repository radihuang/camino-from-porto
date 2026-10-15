"""把一段路的原始照片／影片處理成網站用的版本。

用法：
    uv run python scripts/prepare_media.py photos/01_Porto-Labruge day01

- 照片（jpg/jpeg/heic/png）→ photos/day01/<名稱>.jpg（長邊 1920）＋ photos/day01/thumbs/（長邊 600）
- 影片（mov/mp4）→ videos/day01/<名稱>.mp4（720p H.264）＋ 同名 .jpg 封面
- 一律清掉 EXIF 與影片中繼資料（含 GPS）；原始檔不動，原始資料夾不進版控
- 已處理過的檔案會略過，重跑安全
- 最後印出可以直接貼進 stages/day01.md 的區塊
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

ROOT = Path(__file__).resolve().parent.parent
PHOTO_EXT = {".jpg", ".jpeg", ".heic", ".png"}
VIDEO_EXT = {".mov", ".mp4", ".m4v"}


def save_jpeg(img, dest, long_edge):
    img = img.copy()
    img.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # 不傳 exif=，Pillow 就不會寫出任何 EXIF
    img.convert("RGB").save(dest, "JPEG", quality=82, optimize=True, progressive=True)


def do_photo(src, stage):
    dest = ROOT / "photos" / stage / f"{src.stem}.jpg"
    if not dest.exists():
        with Image.open(src) as im:
            img = ImageOps.exif_transpose(im)  # 先依 EXIF 轉正，再丟掉 EXIF
            save_jpeg(img, dest, 1920)
            save_jpeg(img, dest.parent / "thumbs" / dest.name, 600)
    return dest


def do_video(src, stage):
    dest = ROOT / "videos" / stage / f"{src.stem}.mp4"
    poster = dest.with_suffix(".jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-i", str(src),
            "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "-1", "-map_chapters", "-1",
            "-vf", "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'",
            "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-maxrate", "1500k", "-bufsize", "3000k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", str(dest),
        ], check=True)
    if not poster.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(dest), "-frames:v", "1",
                        "-map_metadata", "-1", "-q:v", "4", str(poster)], check=True)
    return dest


def main(src_dir, stage):
    src_dir = Path(src_dir)
    files = sorted(p for p in src_dir.iterdir() if p.is_file() and not p.name.startswith("."))
    photos, videos, skipped = [], [], []
    for f in files:
        ext = f.suffix.lower()
        if ext in PHOTO_EXT:
            photos.append(do_photo(f, stage))
        elif ext in VIDEO_EXT:
            videos.append(do_video(f, stage))
        else:
            skipped.append(f.name)

    size = sum(p.stat().st_size for p in photos + videos) / 1e6
    print(f"照片 {len(photos)} 張、影片 {len(videos)} 支，輸出共 {size:.1f} MB")
    if skipped:
        print("略過（不認得的格式）：", ", ".join(skipped))
    if photos:
        print("\n```gallery")
        for p in photos:
            print(f"{stage}/{p.name} | ")
        print("```")
    if videos:
        print("\n```video")
        for v in videos:
            print(f"{stage}/{v.name} | ")
        print("```")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
