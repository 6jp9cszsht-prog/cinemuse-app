#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未明 収益キット適用スクリプト(冪等・非破壊)

リポジトリのルートで実行してください:  python3 kit/apply.py

やること:
  1. .github/workflows/announce.yml と scripts/announce_x.py を配置(①X自動投稿)
  2. index.html の購読セクションにメールフォームを挿入(②メール購読)
  3. index.html のフッター直前に「支援と書架」セクションを挿入(③支援+BOOTH)
  4. ナビに「支援」リンクを追加
  5. style.css に収益用CSSを追記
やらないこと:
  - 既存の夜(nXX.html)・日付・feed.xml・sitemap.xml への変更は一切なし
すべての挿入はマーカーで冪等化されており、二度実行しても壊れません。
"""
import pathlib, shutil, sys

KIT = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path.cwd()

def die(msg):
    print("中止:", msg); sys.exit(1)

idx_p = ROOT / "index.html"
css_p = ROOT / "style.css"
if not idx_p.exists() or not css_p.exists():
    die("index.html / style.css が見つかりません。リポジトリのルートで実行してください。")

changed = []

# 1) ワークフローとスクリプト
wf_dst = ROOT / ".github/workflows/announce.yml"
sc_dst = ROOT / "scripts/announce_x.py"
for src, dst in [(KIT/".github/workflows/announce.yml", wf_dst), (KIT/"scripts/announce_x.py", sc_dst)]:
    if dst.exists():
        print("既に存在(スキップ):", dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        changed.append(str(dst)); print("配置:", dst)

idx = idx_p.read_text(encoding="utf-8")

# 2) メールフォーム(RSSリンクの直後)
if "mimei:mail-form" in idx:
    print("メールフォーム: 既に挿入済み")
else:
    anchor = 'RSSで購読する →</a>'
    if anchor not in idx:
        die("購読セクションのRSSリンクが見つかりません(index.htmlの構造が想定と異なります)")
    form = (KIT/"subscribe-form.html").read_text(encoding="utf-8")
    idx = idx.replace(anchor, anchor + "\n" + form, 1)
    changed.append("index.html(mail-form)"); print("挿入: メールフォーム")

# 3) 支援と書架(フッター直前)
if "mimei:support" in idx:
    print("支援セクション: 既に挿入済み")
else:
    anchor = '<footer class="op-foot">'
    if anchor not in idx:
        die("フッターが見つかりません(index.htmlの構造が想定と異なります)")
    sec = (KIT/"support-section.html").read_text(encoding="utf-8")
    idx = idx.replace(anchor, sec + "\n" + anchor, 1)
    changed.append("index.html(support)"); print("挿入: 支援と書架セクション")

# 4) ナビに「支援」
if 'href="#support"' in idx:
    print("ナビ: 既に追加済み")
else:
    anchor = '<a href="#follow">購読</a>'
    if anchor in idx:
        idx = idx.replace(anchor, anchor + '\n    <a href="#support">支援</a>', 1)
        changed.append("index.html(nav)"); print("追加: ナビ「支援」")
    else:
        print("注意: ナビの購読リンクが見つからず、ナビ追加のみスキップしました")

idx_p.write_text(idx, encoding="utf-8")

# 5) CSS追記
css = css_p.read_text(encoding="utf-8")
if "mimei:monetize" in css:
    print("CSS: 既に追記済み")
else:
    css_p.write_text(css + (KIT/"monetize.css").read_text(encoding="utf-8"), encoding="utf-8")
    changed.append("style.css"); print("追記: 収益用CSS")

print("\n=== 適用完了 ===")
print("変更:", changed if changed else "なし(すべて適用済みでした)")
print("""
残っているのは、あなたにしかできない5点の差し替えです:
  [1] X自動投稿   : リポジトリ Settings → Secrets → Actions に
                    X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET
  [2] メール購読  : index.html 内の BUTTONDOWN_USERNAME を自分のIDに
  [3] 支援ボタン  : SUPPORT_URL を Ko-fi か OFUSE のURLに
  [4] 書架       : BOOTH_URL_VOL1 / VOL2 / VOL3 を出品URLに
詳細は kit/README-money.md を参照。""")
