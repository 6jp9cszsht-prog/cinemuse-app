#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未明 「今夜の一冊」注入キット(冪等・非破壊)

リポジトリのルートで実行:  python3 apply_tana.py

やること:
  - 各夜(n01〜n18)の「今夜の問い」の直後に、その夜の同行者の一冊を挿入
  - Amazon検索リンク方式(版違い・絶版によるリンク切れが起きない)
  - ステマ規制対応のPR表記を各ブロックに同梱
  - style.css に意匠を追記
やらないこと:
  - 記事本文・日付・既存要素への変更は一切なし
すべてマーカーで冪等化。AMAZON_TAG はプレースホルダ(後で1回置換)。
"""
import pathlib, sys, urllib.parse

ROOT = pathlib.Path.cwd()

# ---- 全18夜の選書(同行者の原典) ----
BOOKS = {
  1:  ("『時間と自由』",            "アンリ・ベルクソン",     "時間と自由 ベルクソン"),
  2:  ("『中動態の世界』",          "國分功一郎",             "中動態の世界 國分功一郎"),
  3:  ("『複製技術時代の芸術作品』","ヴァルター・ベンヤミン", "複製技術時代の芸術作品 ベンヤミン"),
  4:  ("『正常と病理』",            "ジョルジュ・カンギレム", "正常と病理 カンギレム"),
  5:  ("『貨幣の哲学』",            "ゲオルク・ジンメル",     "貨幣の哲学 ジンメル"),
  6:  ("『人間の条件』",            "ハンナ・アーレント",     "人間の条件 アーレント"),
  7:  ("『告白』",                  "アウグスティヌス",       "告白 アウグスティヌス 岩波"),
  8:  ("『パンセ』",                "ブレーズ・パスカル",     "パンセ パスカル"),
  9:  ("『ニコマコス倫理学』",      "アリストテレス",         "ニコマコス倫理学"),
  10: ("『実存主義とは何か』",      "J=P・サルトル",          "実存主義とは何か サルトル"),
  11: ("『人間の学としての倫理学』","和辻哲郎",               "人間の学としての倫理学 和辻哲郎"),
  12: ("『道徳の系譜学』",          "フリードリヒ・ニーチェ", "道徳の系譜 ニーチェ"),
  13: ("『ニコマコス倫理学』",      "アリストテレス",         "ニコマコス倫理学"),
  14: ("『暗黙知の次元』",          "マイケル・ポランニー",   "暗黙知の次元 ポランニー"),
  15: ("『人間の条件』",            "ハンナ・アーレント",     "人間の条件 アーレント"),
  16: ("『どこでもないところからの眺め』","トマス・ネーゲル", "どこでもないところからの眺め ネーゲル"),
  17: ("『定本 想像の共同体』",     "ベネディクト・アンダーソン","想像の共同体 アンダーソン"),
  18: ("『道徳感情論』",            "アダム・スミス",         "道徳感情論 アダム・スミス"),
}

CSS_MARK = "mimei:tana"
CSS = """
/* ===== mimei:tana(今夜の一冊)===== */
.tana{margin:0 0 3.5rem;padding:1.9rem 0 1.7rem;border-bottom:1px solid var(--hair)}
.tana .koma{margin-bottom:1.2rem}
.tana-book{display:flex;flex-wrap:wrap;align-items:baseline;gap:.4em 1em;
  border:1px solid var(--hair);border-radius:3px;padding:1.3rem 1.4rem;
  transition:border-color .3s,background .3s}
.tana-book:hover{border-color:var(--akebono-soft);background:rgba(238,146,119,.05)}
.tana-book .tt{font-weight:700;font-size:16.5px;letter-spacing:.04em}
.tana-book .au{font-size:12.5px;color:var(--dim);letter-spacing:.08em}
.tana-book .go{margin-left:auto;font-family:var(--gothic);font-weight:400;
  font-size:11.5px;letter-spacing:.2em;color:var(--akebono);white-space:nowrap}
.tana-pr{margin-top:.9rem;font-family:var(--gothic);font-weight:300;
  font-size:10px;letter-spacing:.14em;color:var(--dim);line-height:1.9}
@media (max-width:480px){.tana-book .go{margin-left:0;width:100%}}
"""

def block(n):
    tt, au, q = BOOKS[n]
    url = "https://www.amazon.co.jp/s?k=" + urllib.parse.quote_plus(q) + "&tag=AMAZON_TAG"
    return f'''    <aside class="tana">
      <span class="koma">今夜の一冊</span>
      <a class="tana-book" href="{url}" target="_blank" rel="noopener sponsored">
        <span class="tt">{tt}</span><span class="au">{au}</span><span class="go">Amazonで見る →</span>
      </a>
      <p class="tana-pr">※Amazonのアソシエイトとして、未明は適格販売により収入を得ています。</p>
    </aside>

'''

changed, skipped, missing = [], [], []
for n in range(1, 19):
    p = ROOT / f"n{n:02d}.html"
    if not p.exists():
        missing.append(p.name); continue
    src = p.read_text(encoding="utf-8")
    if 'class="tana"' in src:
        skipped.append(p.name); continue
    anchor = '<nav class="yonav">'
    if anchor not in src:
        print(f"警告: {p.name} に挿入位置が見つからず、スキップ"); continue
    src = src.replace(anchor, block(n) + anchor, 1)
    p.write_text(src, encoding="utf-8")
    changed.append(p.name)

css_p = ROOT / "style.css"
if css_p.exists():
    css = css_p.read_text(encoding="utf-8")
    if CSS_MARK not in css:
        css_p.write_text(css + CSS, encoding="utf-8")
        print("追記: style.css(今夜の一冊の意匠)")
    else:
        print("CSS: 既に追記済み")
else:
    print("警告: style.css が見つかりません。リポジトリのルートで実行してください。")
    sys.exit(1)

print(f"\n挿入: {len(changed)}夜 {changed}")
if skipped: print(f"既に挿入済み: {skipped}")
if missing: print(f"未存在(将来の夜): {missing}")
print("""
残る作業はひとつ:
  Amazonアソシエイト(affiliate.amazon.co.jp)に登録してトラッキングIDを取得し、
  全ファイルの AMAZON_TAG をそのIDに一括置換(例: mimei0a-22)。
置換までの間もリンクは正常に動作します(収益計上されないだけ)。""")
