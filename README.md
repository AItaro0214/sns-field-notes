# SNS FIELD NOTES — Instagram / Threads 観測記録

Instagram / Threads（読み取り専用、トレンド起点）の毎日の観測記録を、ダッシュボード風の静的サイト（GitHub Pages 向け）として公開するためのリポジトリです。

- トップページ：観測日数・累計トピック数などの KPI、日ごとのトップトレンド投稿数のグラフ、複数日にまたがる継続テーマのトラッカー、日別カード一覧
- 日別ページ：その日のトレンド（投稿数を横バーで可視化）、日替わり深掘り、個別投稿から見えたこと、論争・愚痴、示唆
- 数値や内容は観測ログ（`~/workspace/sns-observation/log.md`）に書かれたものだけを使い、捏造しません。投稿数が不明なものは「不明」として扱います。

## 構成

```
data/observations.json   観測ログを構造化したデータ（編集するのはここ）
assets/covers/<date>.jpg 日ごとのカバー画像（例: 2026-11-19.jpg、任意）
build.py                 静的サイト生成スクリプト（Python 標準ライブラリのみ）
docs/                    生成物（GitHub Pages の公開対象）
```

## 毎日の更新手順

1. `data/observations.json` の `days` 配列に、その日分の観測を1件追加する（既存の日の形式に合わせる。継続テーマがあれば `themes` の `phases` にも1行追加）。代表的な投稿の URL が分かる場合は、`trends` や `postNotes` の各エントリにある `url` フィールドに入れると、記事ページに「投稿を見る」リンクが表示される（空なら表示されない）。
2. （任意）カバー画像を `assets/covers/<YYYY-MM-DD>.jpg` に置く。無くてもビルドは通り、サイト側ではプレースホルダ表示になる。
3. ビルドする。

   ```
   python3 build.py
   ```

4. 公開する。

   ```
   git add -A
   git commit -m "観測記録 YYYY-MM-DD を追加"
   git push
   ```

   GitHub Pages の設定で `docs/` ディレクトリ（またはこのリポジトリ全体を配置した先）を公開対象にしてください。

## ローカル確認

```
python3 -m http.server -d docs 8000
# → http://localhost:8000/
```
