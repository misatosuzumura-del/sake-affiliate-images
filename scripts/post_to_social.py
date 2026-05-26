#!/usr/bin/env python3
"""リール(Instagram) / Threads へ動画を投稿するスクリプト。

★ このスクリプトは「.env のあるローカル環境」で実行してください。
   クラウド側には認証情報が無いため投稿できません。

使い方:
    # 1. まず内容確認（公開せず検証だけ）
    python scripts/post_to_social.py --dry-run

    # 2. 問題なければ実際に投稿（--publish が無いと公開しない安全設計）
    python scripts/post_to_social.py --publish              # 両方へ
    python scripts/post_to_social.py --publish --only reel  # リールのみ
    python scripts/post_to_social.py --publish --only threads

.env に必要なキー（お使いの命名に合わせて適宜変更可。環境変数でも可）:
    IG_USER_ID          … Instagram ビジネス/クリエイターアカウントの user id
    IG_ACCESS_TOKEN     … Instagram Graph API の長期トークン
    THREADS_USER_ID     … Threads のユーザーID
    THREADS_ACCESS_TOKEN… Threads API のアクセストークン
    （任意）CAPTION       … 投稿キャプション
    （任意）REEL_VIDEO_URL / THREADS_VIDEO_URL … 動画の公開URL

依存: 標準ライブラリのみ（requests 等は不要）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = "claude/trusting-cerf-6vT9k"
CDN = f"https://cdn.jsdelivr.net/gh/misatosuzumura-del/sake-affiliate-images@{BRANCH}"
DEFAULT_REEL_URL = f"{CDN}/video/reels_9x16.mp4"
DEFAULT_THREADS_URL = f"{CDN}/video/reels_9x16.mp4"
DEFAULT_CAPTION = "新作の日本酒、入荷しました🍶\n購入はプロフィールから（楽天ROOM @yoi.sake）\n#日本酒 #sake #yoisake"

IG_API = "https://graph.facebook.com/v21.0"
TH_API = "https://graph.threads.net/v1.0"


def load_dotenv(path: Path) -> None:
    """.env を環境変数へ読み込む（既存の環境変数は上書きしない）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def need(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"環境変数 {name} が未設定です（.env を確認してください）")
    return v


def _post(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(url: str, params: dict) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=60) as r:
        return json.loads(r.read().decode())


def _wait_ready(base: str, container_id: str, token: str, label: str) -> None:
    for _ in range(40):  # 最大 ~6.5 分
        info = _get(f"{base}/{container_id}", {"fields": "status_code,status", "access_token": token})
        status = info.get("status_code") or info.get("status")
        print(f"  [{label}] container {container_id}: {status}")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            sys.exit(f"  [{label}] 動画処理に失敗: {info}")
        time.sleep(10)
    sys.exit(f"  [{label}] タイムアウト（動画処理が完了しませんでした）")


def post_reel(video_url: str, caption: str, dry: bool) -> None:
    user_id, token = need("IG_USER_ID"), need("IG_ACCESS_TOKEN")
    print(f"[Instagram Reel] video_url={video_url}")
    if dry:
        print("  (dry-run: 実投稿はスキップ)")
        return
    created = _post(f"{IG_API}/{user_id}/media", {
        "media_type": "REELS", "video_url": video_url,
        "caption": caption, "access_token": token,
    })
    cid = created["id"]
    _wait_ready(IG_API, cid, token, "IG")
    res = _post(f"{IG_API}/{user_id}/media_publish", {"creation_id": cid, "access_token": token})
    print(f"  公開完了 media_id={res.get('id')}")


def post_threads(video_url: str, text: str, dry: bool) -> None:
    user_id, token = need("THREADS_USER_ID"), need("THREADS_ACCESS_TOKEN")
    print(f"[Threads] video_url={video_url}")
    if dry:
        print("  (dry-run: 実投稿はスキップ)")
        return
    created = _post(f"{TH_API}/{user_id}/threads", {
        "media_type": "VIDEO", "video_url": video_url,
        "text": text, "access_token": token,
    })
    cid = created["id"]
    _wait_ready(TH_API, cid, token, "Threads")
    res = _post(f"{TH_API}/{user_id}/threads_publish", {"creation_id": cid, "access_token": token})
    print(f"  公開完了 thread_id={res.get('id')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="実際に公開する（無指定なら dry-run 相当で安全）")
    ap.add_argument("--dry-run", action="store_true", help="検証のみ（公開しない）")
    ap.add_argument("--only", choices=["reel", "threads"], help="片方だけ投稿")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    dry = args.dry_run or not args.publish
    if dry:
        print("=== DRY-RUN モード（--publish で実投稿）===")

    caption = os.environ.get("CAPTION", DEFAULT_CAPTION)
    reel_url = os.environ.get("REEL_VIDEO_URL", DEFAULT_REEL_URL)
    threads_url = os.environ.get("THREADS_VIDEO_URL", DEFAULT_THREADS_URL)

    if args.only in (None, "reel"):
        post_reel(reel_url, caption, dry)
    if args.only in (None, "threads"):
        post_threads(threads_url, caption, dry)
    print("done")


if __name__ == "__main__":
    main()
