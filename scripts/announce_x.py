#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未明 — 新しい夜をXへ自動投稿する(feed.xmlの先頭itemを読む)

動作:
  - feed.xml の最新 <item> を読み、.announce_state のGUIDと比較
  - 未投稿なら X API v2 でポストし、.announce_state を更新
  - APIキー未設定なら、設定手順を表示して正常終了(リポジトリを壊さない)
  - DRY_RUN=1 なら投稿せず本文だけ表示(状態も更新しない)
必要なSecrets: X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET
"""
import os, sys, pathlib
import xml.etree.ElementTree as ET

FEED = pathlib.Path("feed.xml")
STATE = pathlib.Path(".announce_state")

def main():
    if not FEED.exists():
        print("feed.xml が見つかりません。リポジトリ直下で実行してください。")
        return 0

    ch = ET.parse(FEED).getroot().find("channel")
    item = ch.find("item")
    if item is None:
        print("feedにitemがありません。")
        return 0

    title = (item.findtext("title") or "").strip()
    link = (item.findtext("link") or "").strip()
    guid = (item.findtext("guid") or link).strip()

    if STATE.exists() and STATE.read_text(encoding="utf-8").strip() == guid:
        print(f"最新の夜は投稿済みです: {title}")
        return 0

    text = f"【未明】新しい夜を公開しました。\n『{title}』\n\n金曜22時、週にひとつの問い。\n{link}"

    if os.environ.get("DRY_RUN") == "1":
        print("--- DRY RUN(投稿しません) ---")
        print(text)
        return 0

    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        print("Xの認証キーが未設定のため、投稿をスキップしました。")
        print("設定手順: developer.x.com で無料アプリを作成し、次の4つを")
        print("リポジトリの Settings → Secrets and variables → Actions に登録:")
        print("  " + " / ".join(keys))
        print("(未設定の間もサイト公開には影響しません)")
        return 0

    import tweepy
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    resp = client.create_tweet(text=text)
    print("投稿しました:", resp.data.get("id"))
    STATE.write_text(guid + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    sys.exit(main())
