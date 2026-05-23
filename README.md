# sake-affiliate-images

yoi.sake の Instagram 自動投稿で使う画像配信リポ。
private な本体リポから参照され、jsDelivr CDN / raw.githubusercontent 経由で Instagram Graph API に渡す。

- `feed/NN.jpg` … フィード投稿用（1:1 補正済み）
- `story/NN.jpg` … ストーリー投稿用（9:16 テキスト合成済み）

更新は本体リポの `scripts/sync_images_repo.py` で行う。
