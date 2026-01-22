import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
from datetime import datetime

# --- 設定とシークレットの読み込み ---
# Streamlit CloudのSecrets機能を使用します
try:
    GENAI_API_KEY = st.secrets["AIzaSyD1rCNYR-adyY6G8M6SYG7cOZBHErDl9b8"]
    TMDB_API_KEY = st.secrets.get("0b829860d77650aa4bf68f3064fab5a8", "") # オプション
except:
    st.error("APIキーが設定されていません。StreamlitのSecretsに設定してください。")
    st.stop()

genai.configure(api_key=GENAI_API_KEY)

# --- 関数群 ---

def get_movie_poster(movie_title):
    """TMDB APIを使って映画のポスター画像を取得する"""
    if not TMDB_API_KEY:
        return None
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}&language=ja-JP"
    try:
        response = requests.get(url).json()
        if response['results']:
            poster_path = response['results'][0].get('poster_path')
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except:
        return None
    return None

def generate_interview_response(history, movie_title):
    """Geminiを使ってインタビューの返答を生成する"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # プロンプトエンジニアリング：優秀な編集者になりきる
    system_prompt = f"""
    あなたは映画感想引き出しアプリ『Muse Memo』の専属編集者です。
    ユーザーは『{movie_title}』という映画を見ました。
    親しみやすく、かつ知的なトーンで、ユーザーの感動や思考を深掘りする質問をしてください。
    
    ルール:
    1. 1回につき質問は1つだけ。
    2. ユーザーの前の発言に共感してから質問する。
    3. 核心を突く質問をする（映像、音楽、脚本、演技など）。
    4. 会話が十分深まったと判断したら（あるいは3ターン以上経過したら）、最後に特別なトークン [END] を出力に含めて終了を宣言する。
    """
    
    messages = [{'role': 'user', 'parts': [system_prompt]}]
    for chat in history:
        role = 'model' if chat['role'] == 'ai' else 'user'
        messages.append({'role': role, 'parts': [chat['text']]})
    
    response = model.generate_content(messages)
    return response.text

def generate_final_content(history, movie_title):
    """会話ログからレビューと短歌を生成する"""
    model = genai.GenerativeModel('gemini-1.5-pro') # 仕上げは高性能なProモデルで
    
    conversation_text = "\n".join([f"{c['role']}: {c['text']}" for c in history])
    
    prompt = f"""
    以下の映画『{movie_title}』に関するインタビューログを元に、2つのコンテンツを作成してください。
    
    ログ:
    {conversation_text}
    
    作成物:
    1. **レビュー記事**: ブログにそのまま載せられるような、感情豊かで洞察に満ちた400字程度のレビュー。タイトルもつけて。
    2. **短歌**: 映画の核心感情を詠んだ短歌（5-7-5-7-7）を1首。
    
    出力形式はマークダウンで見やすく。
    """
    response = model.generate_content(prompt)
    return response.text

# --- アプリケーション本体 ---

st.set_page_config(page_title="Muse Memo", page_icon="🎬", layout="centered")

# カスタムCSS（スマホで見やすく、リッチにする）
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 0; padding-bottom: 20px;}
    .movie-card {background-color: #262730; padding: 20px; border-radius: 10px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

st.title("🎬 Muse Memo")

# セッション管理
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "interview_stage" not in st.session_state:
    st.session_state.interview_stage = 0 # 0:Top, 1:Chat, 2:Result
if "movie_title" not in st.session_state:
    st.session_state.movie_title = ""

# --- 画面遷移ロジック ---

# 1. トップ画面（新規作成）
if st.session_state.interview_stage == 0:
    st.subheader("今日はどの映画の世界にいましたか？")
    movie_input = st.text_input("映画のタイトルを入力...", placeholder="例: 天空の城ラピュタ")
    
    if st.button("記録を始める", use_container_width=True):
        if movie_input:
            st.session_state.movie_title = movie_input
            st.session_state.interview_stage = 1
            # 最初の挨拶
            first_msg = f"『{movie_input}』ですね！鑑賞お疲れ様でした。見終わった今、一番心に残っているのはどんな「色」や「音」ですか？"
            st.session_state.chat_history.append({"role": "ai", "text": first_msg})
            st.rerun()

# 2. インタビュー画面
elif st.session_state.interview_stage == 1:
    st.progress(len(st.session_state.chat_history) * 10, text="思考を言語化中...")
    
    # チャット表示
    for chat in st.session_state.chat_history:
        avatar = "🤖" if chat["role"] == "ai" else "👤"
        with st.chat_message(chat["role"], avatar=avatar):
            st.write(chat["text"])

    # 入力フォーム
    if user_input := st.chat_input("ここに入力（音声入力がおすすめ）"):
        # ユーザーの入力を追加
        st.session_state.chat_history.append({"role": "user", "text": user_input})
        
        # AIの応答を生成
        with st.spinner("AIが編集中..."):
            ai_response = generate_interview_response(st.session_state.chat_history, st.session_state.movie_title)
        
        # 終了判定
        if "[END]" in ai_response or len(st.session_state.chat_history) > 8:
            ai_response = ai_response.replace("[END]", "")
            st.session_state.chat_history.append({"role": "ai", "text": ai_response})
            st.session_state.interview_stage = 2 # 結果画面へ
            st.rerun()
        else:
            st.session_state.chat_history.append({"role": "ai", "text": ai_response})
            st.rerun()

# 3. 結果発表画面
elif st.session_state.interview_stage == 2:
    poster_url = get_movie_poster(st.session_state.movie_title)
    
    if poster_url:
        st.image(poster_url, width=200)
    
    st.title(f"『{st.session_state.movie_title}』")
    st.caption(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    
    # 最終コンテンツ生成
    if "final_content" not in st.session_state:
        with st.spinner("最高のレビューと短歌を執筆中..."):
            st.session_state.final_content = generate_final_content(st.session_state.chat_history, st.session_state.movie_title)
    
    st.markdown("---")
    st.markdown(st.session_state.final_content)
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("もう一度記録する"):
            st.session_state.clear()
            st.rerun()
    with col2:
        # ここに将来アフィリエイトリンクなどを挟めます
        st.link_button("Amazon Primeで見る", f"https://www.amazon.co.jp/s?k={st.session_state.movie_title}")
