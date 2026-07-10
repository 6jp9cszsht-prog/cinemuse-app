#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未明 — 予約公開スクリプト

各 nXX.html の <meta property="article:published_time"> を読み、
公開時刻を過ぎているのに feed.xml に載っていない夜を自動で「公開」する。

公開 = 以下を編集(すべて冪等):
  index.html    最新夜の大カードを差し替え(前の最新は通常カードへ降格)
                近日欄から該当ブロックを削除
                ヒーローの「最新 …」リンクを更新
                問いの棚の先頭に「今夜の問い」を追加
  n(N-1).html   「次の夜」の ghost を実リンクに
  feed.xml      先頭に item を追加、lastBuildDate を更新
  sitemap.xml   url を追加、トップの lastmod を更新

記事本文・日付には一切触れない。書き込みは全処理の最後にまとめて行うため、
途中で異常があってもファイルは壊れない。

使い方:
  python3 scripts/publish_night.py             # 時が来た夜をすべて公開
  python3 scripts/publish_night.py --dry-run   # 変更を表示するだけ
  python3 scripts/publish_night.py --night 15  # 特定の夜を強制公開
"""
import re, sys, json, glob, pathlib, argparse, datetime, email.utils

ROOT = pathlib.Path.cwd()
SITE = "https://mimei.page"
JST = datetime.timezone(datetime.timedelta(hours=9))


def die(msg):
    print(f"中止: {msg}")
    sys.exit(1)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def read_night(path):
    s = path.read_text(encoding="utf-8")

    def find(pat, label, default=None):
        m = re.search(pat, s, re.S)
        if not m:
            if default is not None:
                return default
            die(f"{path.name}: {label} が見つかりません")
        return m.group(1).strip()

    meta_blk = find(r'<div class="meta"[^>]*>(.*?)</div>', "meta")
    spans = re.findall(r"<span[^>]*>(.*?)</span>", meta_blk, re.S)
    if len(spans) < 3:
        die(f"{path.name}: meta の span が3つありません")
    return {
        "file": path.name,
        "n": int(path.name[1:3]),
        "ya": strip_tags(spans[0]),
        "cat": strip_tags(spans[1]),
        "date": strip_tags(spans[2]),
        "title": strip_tags(find(r"<h1>(.*?)</h1>", "h1")),
        "desc": find(r'<meta name="description" content="([^"]+)"', "description"),
        "toi": strip_tags(find(r'<aside class="toi">.*?<p>(.*?)</p>', "toi", "")),
        "pub": datetime.datetime.fromisoformat(
            find(r'<meta property="article:published_time" content="([^"]+)"', "published_time")
        ),
    }


def toc_line(night):
    p = ROOT / "scripts" / "toc_lines.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        key = f"n{night['n']:02d}"
        if key in d:
            return d[key]
    parts = [x for x in re.split(r"(?<=。)", night["desc"]) if x.strip()]
    return "——" + "".join(parts[:2])


def feat_html(night, line):
    return (
        f'      <a class="op-feat" href="{night["file"]}">\n'
        f'        <div class="op-meta"><span class="ya">最新 — {night["ya"]}</span>'
        f'<span>{night["cat"]}</span><span>{night["date"]}</span></div>\n'
        f'        <h3>{night["title"]}</h3>\n'
        f'        <p class="op-line">{line}</p>\n'
        f'        <span class="op-read">読む →</span>\n'
        f"      </a>"
    )


def card_from_feat(feat_block):
    """最新の大カードを通常カードへ降格"""
    c = feat_block.replace('class="op-feat"', 'class="op-card"')
    c = re.sub(r'<span class="ya">最新 — ', '<span class="ya">', c)
    c = re.sub(r'\s*<span class="op-read">.*?</span>\n', "\n", c, flags=re.S)
    return "\n".join(("  " + ln) if ln.strip() else ln for ln in c.split("\n"))


def publish(night, idx, feed, sm, prevs):
    f, n, title = night["file"], night["n"], night["title"]
    line = toc_line(night)
    log = []

    if f'href="{f}"' in idx:
        log.append("目次に掲載済み(スキップ)")
    else:
        m = re.search(r'      <a class="op-feat".*?</a>', idx, re.S)
        if m:
            demoted = card_from_feat(m.group(0))
            idx = idx[: m.start()] + feat_html(night, line) + idx[m.end():]
            g = re.search(r'(<div class="op-grid">\s*\n)', idx)
            if not g:
                die("index.html: op-grid が見つかりません")
            idx = idx[: g.end(1)] + demoted + "\n" + idx[g.end(1):]
            log.append("最新カードを差し替え(旧最新は通常カードへ)")
        else:
            g = re.search(r'(<div class="op-grid">\s*\n)', idx)
            if not g:
                die("index.html: op-feat も op-grid も見つかりません")
            idx = idx[: g.end(1)] + card_from_feat(feat_html(night, line)) + "\n" + idx[g.end(1):]
            log.append("目次カードを追加")

    soon = re.search(
        r'\s*<div class="op-card op-soon">(?:(?!<div class="op-card op-soon">).)*?<h3>'
        + re.escape(title) + r"</h3>\s*</div>", idx, re.S)
    if not soon:
        soon = re.search(
            r'\s*<li class="soon">(?:(?!<li class="soon">).)*?<h3>'
            + re.escape(title) + r"</h3>.*?</li>", idx, re.S)
    if soon:
        idx = idx[: soon.start()] + idx[soon.end():]
        log.append("近日欄から削除")

    m = re.search(r'<a class="op-latest" href="[^"]+">[^<]*</a>', idx)
    if m:
        idx = idx[: m.start()] + f'<a class="op-latest" href="{f}">最新 {night["ya"]}「{title}」→</a>' + idx[m.end():]
        log.append("ヒーローの最新リンクを更新")

    if night["toi"] and f'class="op-toi" href="{f}"' not in idx:
        m = re.search(r'( *)<a class="op-toi"', idx)
        if m:
            row = (f'{m.group(1)}<a class="op-toi" href="{f}"><span class="q">{night["toi"]}</span>'
                   f'<span class="n">— {night["ya"]}</span></a>\n')
            idx = idx[: m.start()] + row + idx[m.start():]
            log.append("問いの棚に追加")

    prev_p = ROOT / f"n{n-1:02d}.html"
    if prev_p.exists():
        prev = prevs.get(prev_p, prev_p.read_text(encoding="utf-8"))
        g = re.search(r'<span class="ghost">[^<]*?' + re.escape(night["ya"]) + r"[^<]*?</span>", prev)
        if g:
            prevs[prev_p] = prev[: g.start()] + f'<a href="{f}">{night["ya"]} {title} →</a>' + prev[g.end():]
            log.append(f"n{n-1:02d}: 次の夜を実リンクに")

    pubdate = email.utils.format_datetime(night["pub"])
    if f"{SITE}/{f}" in feed:
        log.append("feedに掲載済み(スキップ)")
    else:
        item = (f"\n  <item>\n    <title>{title}</title>\n"
                f"    <link>{SITE}/{f}</link>\n    <guid>{SITE}/{f}</guid>\n"
                f"    <pubDate>{pubdate}</pubDate>\n"
                f"    <description>{night['desc']}</description>\n  </item>")
        if "\n  <item>" not in feed:
            die("feed.xml: <item> が見つかりません")
        feed = feed.replace("\n  <item>", item + "\n  <item>", 1)
        feed = re.sub(r"<lastBuildDate>.*?</lastBuildDate>",
                      f"<lastBuildDate>{pubdate}</lastBuildDate>", feed, count=1)
        log.append("feedに追加")

    lastmod = night["pub"].astimezone(JST).strftime("%Y-%m-%d")
    if f"{SITE}/{f}" in sm:
        log.append("sitemapに掲載済み(スキップ)")
    else:
        m = re.search(r"[ \t]*<url><loc>" + re.escape(SITE) + r"/n\d+\.html</loc>", sm)
        if not m:
            die("sitemap.xml: 記事URLが見つかりません")
        sm = sm[: m.start()] + f"  <url><loc>{SITE}/{f}</loc><lastmod>{lastmod}</lastmod></url>\n" + sm[m.start():]
        log.append("sitemapに追加")
    sm = re.sub(r"(<loc>" + re.escape(SITE) + r"/</loc><lastmod>)[^<]+(</lastmod>)",
                rf"\g<1>{lastmod}\g<2>", sm, count=1)

    for x in log:
        print(f"  {night['ya']}: {x}")
    return idx, feed, sm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--night", type=int, default=None)
    a = ap.parse_args()

    for req in ("index.html", "feed.xml", "sitemap.xml"):
        if not (ROOT / req).exists():
            die(f"{req} が見つかりません。リポジトリのルートで実行してください")

    now = datetime.datetime.now(JST)
    idx = (ROOT / "index.html").read_text(encoding="utf-8")
    feed = (ROOT / "feed.xml").read_text(encoding="utf-8")
    sm = (ROOT / "sitemap.xml").read_text(encoding="utf-8")

    nights = [read_night(pathlib.Path(p)) for p in sorted(glob.glob("n[0-9][0-9].html"))]
    if a.night:
        due = [x for x in nights if x["n"] == a.night]
        if not due:
            die(f"n{a.night:02d}.html が見つかりません")
    else:
        due = [x for x in nights if x["pub"] <= now and f"{SITE}/{x['file']}" not in feed]

    if not due:
        print(f"公開すべき夜はありません(現在 {now:%Y-%m-%d %H:%M} JST)")
        return 0

    print(f"公開対象: {', '.join(x['ya'] for x in due)}" + ("  [DRY RUN]" if a.dry_run else ""))
    prevs = {}
    for night in sorted(due, key=lambda x: x["n"]):
        idx, feed, sm = publish(night, idx, feed, sm, prevs)

    if a.dry_run:
        print("完了(何も書き込んでいません)")
        return 0

    (ROOT / "index.html").write_text(idx, encoding="utf-8")
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sm, encoding="utf-8")
    for p, s in prevs.items():
        p.write_text(s, encoding="utf-8")
    print("完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
