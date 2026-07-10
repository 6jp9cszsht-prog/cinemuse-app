#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未明 — 新しい夜をBlueskyへ自動投稿する

動作:
  - feed.xml の最新 <item> を読み、.announce_state のGUIDと比較
  - 未投稿なら AT Protocol で投稿し、.announce_state を更新
  - 認証情報が未設定なら、設定手順を表示して正常終了
  - DRY_RUN=1 なら投稿せず、送信予定のペイロードを表示

必要なSecrets:
  BSKY_HANDLE        例: mimei.page  (または xxxx.bsky.social)
  BSKY_APP_PASSWORD  Bluesky設定 → アプリパスワード で発行(xxxx-xxxx-xxxx-xxxx)

補足: リポジトリ内のfeed.xmlのURLは環境によりプレースホルダの場合があるため、
      workflowがPages APIから実URL(SITE_BASE)を取得して渡す。独自ドメインにも追従。
"""
import os, sys, json, pathlib, datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

FEED = pathlib.Path("feed.xml")
STATE = pathlib.Path(".announce_state")
PDS = "https://bsky.social"
MAX_GRAPHEMES = 300


def read_latest():
    """feed.xmlの最新itemを返す"""
    ch = ET.parse(FEED).getroot().find("channel")
    item = ch.find("item")
    if item is None:
        return None
    return {
        "title": (item.findtext("title") or "").strip(),
        "link": (item.findtext("link") or "").strip(),
        "guid": (item.findtext("guid") or item.findtext("link") or "").strip(),
        "desc": (item.findtext("description") or "").strip(),
    }


def resolve_link(raw_link):
    """SITE_BASEがあれば実URLを合成する"""
    base = os.environ.get("SITE_BASE", "").strip().rstrip("/")
    if not base:
        return raw_link
    fname = urlparse(raw_link).path.rsplit("/", 1)[-1]
    return f"{base}/{fname}"


def build_text(title, link):
    """投稿本文を組む(300字以内)"""
    return (
        "【未明】新しい夜を公開しました。\n"
        f"『{title}』\n\n"
        "金曜22時、週にひとつの問い。\n"
        f"{link}"
    )


def link_facets(text, link):
    """本文中のURLをリンクにするfacet(UTF-8バイトオフセット)"""
    b = text.encode("utf-8")
    target = link.encode("utf-8")
    start = b.find(target)
    if start < 0:
        return []
    return [{
        "index": {"byteStart": start, "byteEnd": start + len(target)},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
    }]


def build_record(title, link, desc, thumb_blob=None, now=None):
    """投稿レコード(送信ペイロード)を組む"""
    text = build_text(title, link)
    external = {"uri": link, "title": f"{title} — 未明", "description": desc[:280]}
    if thumb_blob:
        external["thumb"] = thumb_blob
    ts = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {
        "$type": "app.bsky.feed.post",
        "text": text,
        "facets": link_facets(text, link),
        "langs": ["ja"],
        "createdAt": ts,
        "embed": {"$type": "app.bsky.embed.external", "external": external},
    }


def main():
    if not FEED.exists():
        print("feed.xml が見つかりません。リポジトリ直下で実行してください。")
        return 0

    post = read_latest()
    if not post:
        print("feedにitemがありません。")
        return 0

    link = resolve_link(post["link"])
    if "YOURNAME" in link:
        print("警告: SITE_BASE未設定で、feedのリンクがプレースホルダのままです。スキップします。")
        return 0

    if STATE.exists() and STATE.read_text(encoding="utf-8").strip() == post["guid"]:
        print(f"最新の夜は投稿済みです: {post['title']}")
        return 0

    text = build_text(post["title"], link)
    if len(text) > MAX_GRAPHEMES:
        print(f"警告: 本文が{len(text)}字で上限{MAX_GRAPHEMES}を超えています。")

    if os.environ.get("DRY_RUN") == "1":
        rec = build_record(post["title"], link, post["desc"])
        print("--- DRY RUN(投稿しません) ---")
        print(text)
        print("\n--- facets ---")
        print(json.dumps(rec["facets"], ensure_ascii=False, indent=1))
        return 0

    handle = os.environ.get("BSKY_HANDLE", "").strip()
    app_pw = os.environ.get("BSKY_APP_PASSWORD", "").strip()
    if not handle or not app_pw:
        print("Blueskyの認証情報が未設定のため、投稿をスキップしました。")
        print("設定手順:")
        print("  1. bsky.app でアカウント作成")
        print("  2. 設定 → プライバシーとセキュリティ → アプリパスワード → 追加")
        print("  3. リポジトリの Settings → Secrets and variables → Actions に登録:")
        print("     BSKY_HANDLE / BSKY_APP_PASSWORD")
        print("(未設定の間もサイト公開には影響しません)")
        return 0

    import requests

    # 1) セッション作成
    r = requests.post(
        f"{PDS}/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_pw},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"認証に失敗しました({r.status_code}): {r.text[:300]}")
        print("ハンドルとアプリパスワードを確認してください(通常のログインパスワードは使えません)")
        return 1
    sess = r.json()
    jwt, did = sess["accessJwt"], sess["did"]
    auth = {"Authorization": f"Bearer {jwt}"}

    # 2) OGP画像をカードのサムネイルとしてアップロード(失敗しても投稿は続行)
    thumb = None
    base = os.environ.get("SITE_BASE", "").strip().rstrip("/")
    if base:
        try:
            img = requests.get(f"{base}/ogp.png", timeout=30)
            if img.status_code == 200 and len(img.content) < 976_560:
                up = requests.post(
                    f"{PDS}/xrpc/com.atproto.repo.uploadBlob",
                    headers={**auth, "Content-Type": "image/png"},
                    data=img.content,
                    timeout=60,
                )
                if up.status_code == 200:
                    thumb = up.json().get("blob")
                    print("OGP画像をカードに添付しました")
        except Exception as e:
            print(f"OGP画像の添付をスキップしました: {e}")

    # 3) 投稿
    record = build_record(post["title"], link, post["desc"], thumb_blob=thumb)
    r = requests.post(
        f"{PDS}/xrpc/com.atproto.repo.createRecord",
        headers=auth,
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"投稿に失敗しました({r.status_code}): {r.text[:300]}")
        return 1

    uri = r.json().get("uri", "")
    rkey = uri.rsplit("/", 1)[-1] if uri else ""
    print("投稿しました: " + (f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else uri))
    STATE.write_text(post["guid"] + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
