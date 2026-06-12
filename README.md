# 未明 — 公開・運用ガイド(スマホ完結版)

わかる、の少し手前で書く。週にひとつの問いを置いていく哲学エッセイ。

## 構成

フォルダなしの平置き構成(スマホの一括アップロード対応)。
HTML 8(記事6+表紙+404)/ feed.xml / sitemap.xml / robots.txt / style.css / 画像3 / deploy.yml(ワークフローのコピー元)

URLの置換作業は不要です。デプロイ時に GitHub Actions が本番URLを自動検知して、
canonical・OGP・RSS・sitemap・robots すべてに焼き込みます。
独自ドメインに切り替えた場合も、再デプロイするだけで自動追従します。

## 公開手順(スマホのブラウザだけで完結・約10分)

1. このzipをスマホで解凍(iPhoneはファイルAppでタップ、AndroidはFiles)
2. ブラウザで github.com → New repository → 名前は自由(例: mimei)→ **Public** → Create
3. リポジトリで Add file → **Upload files** → 解凍したファイルを**全部**選択 → Commit
4. アップ後、Add file → **Create new file** → ファイル名欄に
   `.github/workflows/deploy.yml`
   と入力 → 下のYAML(またはルートの deploy.yml の中身)を貼り付け → Commit
5. 1〜2分でActionsが走り、公開完了。URLは Actions の完了画面、
   または Settings → Pages に表示されます

万一サイトが表示されない場合だけ: Settings → Pages → Source を **GitHub Actions** に変更して、Actionsタブから deploy を Re-run。

```yaml
name: deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure Pages
        id: pages
        uses: actions/configure-pages@v5
        with:
          enablement: true

      - name: Bake real URL into files
        run: |
          BASE="${{ steps.pages.outputs.base_url }}"
          BASE_NOSCHEME="${BASE#https://}"
          find . -maxdepth 1 -type f \( -name "*.html" -o -name "*.xml" -o -name "robots.txt" \) \
            -exec sed -i "s|https://YOURNAME.github.io/mimei|${BASE}|g; s|YOURNAME.github.io/mimei|${BASE_NOSCHEME}|g" {} +
          rm -f README.md deploy.yml

      - uses: actions/upload-pages-artifact@v3
        with:
          path: .

      - name: Deploy
        id: deployment
        uses: actions/deploy-pages@v4
```

## 毎週金曜の更新(スマホで2分)

新しい夜を書いたら、**変更のあったファイル一式**(例: n07.html、index.html、feed.xml、sitemap.xml)を
リポジトリの Add file → Upload files で選択するだけ。
**同名ファイルは自動で上書き**され、pushをトリガーにActionsが再デプロイします。
編集画面でのコピペ作業はゼロ。

22時ぴったりに公開したい週は、そのタイミングでUploadすればOK。

## メモ

- 第四〜六夜(6/19・6/26・7/3付)は仕込み済み。各金曜まで隠したい場合は該当ファイルを抜いてアップし、当日に追加アップ。気にしないなら全部出して構わない(在庫が見える棚も悪くない)
- 検索流入を急ぎたければ、公開後に Google Search Console へ sitemap.xml を登録
- 今後の予定: 第七夜「そのうち」という時間(7/10)、第八夜 退屈について(7/17)
