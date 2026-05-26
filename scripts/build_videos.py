#!/usr/bin/env python3
"""投稿用動画ビルダー。

feed/ と story/ の画像から Instagram 投稿用の動画を生成する。
- video/reels_9x16.mp4 … 縦型リール/ストーリー用 (1080x1920)
- video/feed_1x1.mp4   … 正方形フィード用 (1080x1080)

演出: テンポ速めのカット切替（ハードカット、ズーム無し）。
無音だと一部環境でリールが弾かれるため、無音の音声トラックを付与する。

ffmpeg は imageio-ffmpeg 同梱バイナリ、無ければ PATH 上のものを使う。
依存: Pillow, imageio-ffmpeg (無ければ ffmpeg を PATH に用意)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SEC_PER_IMAGE = 0.8   # 1枚あたりの表示秒数（テンポ速め）
FPS = 30


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
        if not exe:
            sys.exit("ffmpeg が見つかりません。`pip install imageio-ffmpeg` を実行してください。")
        return exe


def normalize(src_dir: Path, size: tuple[int, int], work: Path) -> list[Path]:
    """画像を一律サイズに整える（cover クロップ）。連番順で返す。"""
    work.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for i, src in enumerate(sorted(src_dir.glob("*.jpg"))):
        im = Image.open(src).convert("RGB")
        tw, th = size
        sw, sh = im.size
        scale = max(tw / sw, th / sh)
        nw, nh = round(sw * scale), round(sh * scale)
        im = im.resize((nw, nh), Image.LANCZOS)
        left, top = (nw - tw) // 2, (nh - th) // 2
        im = im.crop((left, top, left + tw, top + th))
        dst = work / f"{i:03d}.jpg"
        im.save(dst, quality=92)
        out.append(dst)
    return out


def build(frames: list[Path], size: tuple[int, int], out_path: Path, exe: str) -> None:
    w, h = size
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in frames:
            f.write(f"file '{p.as_posix()}'\n")
            f.write(f"duration {SEC_PER_IMAGE}\n")
        # 最後の1枚は duration が無視されるため再掲する
        f.write(f"file '{frames[-1].as_posix()}'\n")
        list_path = f.name

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe, "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", f"fps={FPS},scale={w}:{h},format=yuv420p",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  -> {out_path.relative_to(ROOT)}")


def main() -> None:
    exe = ffmpeg_exe()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        print("reels 9:16 を生成中...")
        reels = normalize(ROOT / "story", (1080, 1920), tmp / "story")
        build(reels, (1080, 1920), ROOT / "video" / "reels_9x16.mp4", exe)

        print("feed 1:1 を生成中...")
        feed = normalize(ROOT / "feed", (1080, 1080), tmp / "feed")
        build(feed, (1080, 1080), ROOT / "video" / "feed_1x1.mp4", exe)
    print("完了")


if __name__ == "__main__":
    main()
