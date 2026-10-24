import os
import sys
import time
import re
import feedparser
import atproto
import google.generativeai as genai
from dotenv import load_dotenv

# ローカルテスト用（GitHub Actions環境では環境変数が直接渡されます）
load_dotenv()

# 環境変数からBlueskyおよびGeminiの認証情報を取得
BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not all([BSKY_HANDLE, BSKY_APP_PASSWORD, GEMINI_API_KEY]):
    print("Error: 必要な環境変数 (BSKY_HANDLE, BSKY_APP_PASSWORD, GEMINI_API_KEY) が設定されていません。")
    sys.exit(1)

# Gemini API の設定（バージョンに依存しない latest 系のモデルを指定）
genai.configure(api_key=GEMINI_API_KEY)
# 必要に応じて gemini-1.5-flash-latest または gemini-1.5-flash を指定
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-3.5-flash-latest')

SYSTEM_PROMPT = """
下記のニュースについて日本語で40文字程度で感想を述べて。若い女性目線で。今風な語彙の話し言葉で。適切な短文のツイート内容で。承知しましたは不要。
""".strip()

def post_to_bluesky(text):
    """Blueskyへ投稿する関数"""
    client = atproto.Client()
    try:
        client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
    except Exception as e:
        print(f"Bluesky Login Error: {e}")
        return

    # Blueskyの最大文字数
    MAX_CHARS = 300
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS-3] + "..."
        
    try:
        client.send_post(text=text)
        print("Bluesky tweet ok")
    except Exception as e:
        print(f"Error posting to Bluesky: {e}")

def ai_func(title, link):
    """Geminiを使って若い女性風の感想を生成し、Blueskyに投稿する"""
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            system_instruction=SYSTEM_PROMPT
        )
        
        response = model.generate_content(title)
        total = response.text.strip()

        # 2行目以降は不要な解説などが入る場合があるため、1行目だけ取得
        total = total.splitlines()[0]
        print(f"生成された感想: {total}")

        msg = f"{total}\n\n{title}\n{link}"

        # 英字や特定のキーワードが多い場合はスキップする制御
        alphacount = len(re.findall(r"[a-zA-Z]", total))
        print('英字の数:', alphacount)
        if '承知' in total or '目線' in total:
            alphacount = 10

        if alphacount < 5:
            print('tweet ok')
            post_to_bluesky(msg)
        else:
            print('条件に合致しないためスキップします')

        print('----')
        print(msg)
        print('----')
    except Exception as e:
        print(f"Gemini API Error: {e}")

def main():
    # Yahoo!ニュース（主要）などのRSS URL
    RSS_URL = "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRE5mTTJRU0FtcGhLQUFQAQ?hl=ja&gl=JP&ceid=JP:ja"

    print(f"Fetching RSS from: {RSS_URL}")
    feed = feedparser.parse(RSS_URL)

    cnt = 0
    print(f"--- {feed.feed.title if 'feed' in feed and 'title' in feed.feed else 'News Feed'} ---")
    
    for entry in feed.entries:
        print(f"タイトル: {entry.title}")
        print(f"リンク: {entry.link}")
        print("-" * 20)

        ai_func(entry.title, entry.link)
        cnt += 1
        
        # GitHub Actionsで実行するため、API制限や過剰負荷を防ぐ短いウェイト
        time.sleep(10)
        
        # 1回の実行で処理するニュースの件数制限（必要に応じて調整）
        if cnt >= 2:
            break

if __name__ == '__main__':
    main()