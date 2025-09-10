# app.py — AA Viewer 完全版

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import base64
import os
import re
from copy import copy

# --- サロゲート除去のみ。encode/decode はしない（AA崩れ防止）
def safe_utf8(s: str) -> str:
    return re.sub(r'[\ud800-\udfff]', '\uFFFD', s)

st.set_page_config(layout="wide")

# ---- フォント（MS UI Gothic woff2 を埋め込み。なければフォールバック）
font_base64 = ""
font_path = os.path.join("static", "MS-UIGothic.woff2")
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
            font_base64 = base64.b64encode(font_data).decode("utf-8")
    except Exception:
        pass

font_css = f"""
<style>
@font-face {{
    font-family: 'AAFont';
    src: url("data:font/woff2;base64,{font_base64}") format('woff2');
    font-weight: normal;
    font-style: normal;
}}
html, body, .stApp {{
    font-family: {'AAFont, ' if font_base64 else ''}monospace;
    font-size: 14px;
    line-height: 1.4;
    background-color: #fdfdfd;
    overflow-x: auto;
}}
pre {{
    white-space: pre;
    overflow-x: auto;
    margin: 0;
}}
.res-block {{
    background-color: transparent;
    border: none;
    padding: 0;
    margin-bottom: 1.2em;
}}
</style>
"""
st.markdown(font_css, unsafe_allow_html=True)
if not font_base64:
    st.warning("フォントが見つかりません。static/MS-UIGothic.woff2 を確認してください。等幅フォントで表示します。")

# ---- URL履歴
if "url_history" not in st.session_state:
    st.session_state["url_history"] = []

st.title("AA Viewer")

st.markdown("#### 🔄 過去のURL履歴")
for old_url in reversed(st.session_state["url_history"]):
    if st.button(old_url, key=f"hist_{old_url}"):
        st.session_state["url"] = old_url

def normalize_url(input_url: str) -> str:
    if not re.match(r'^https?://', input_url):
        return 'http://' + input_url
    return input_url

url = st.text_input("AAページのURLを入力してください（http:// または https://）", key="url")

# ---- 読み込み処理
if st.button("読み込む"):
    if url.strip() == "":
        st.warning("URLを入力してください。")
    elif not url.startswith("http://") and not url.startswith("https://"):
        st.error("URLは http:// または https:// で始めてください。")
    else:
        # 履歴（重複回避・最大5件）
        history = st.session_state["url_history"]
        if url in history:
            history.remove(url)
        history.append(url)
        if len(history) > 5:
            history.pop(0)

        try:
            normalized_url = normalize_url(url)
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(normalized_url, headers=headers, timeout=10)
            # Shift_JIS系は cp932 が安定。未知文字は置換。
            decoded = resp.content.decode("cp932", errors="replace")
            soup = BeautifulSoup(decoded, "html.parser")

            dt_blocks = soup.find_all("dt")
            dd_blocks = soup.find_all("dd")

            posts = []
            for index, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
                # ヘッダ（名前・ID 等）
                dt_text = safe_utf8(dt.get_text(strip=True))

                # 本文：<br> だけ \n に置換、その他は改行入れない
                dd_clone = copy(dd)
                for br in dd_clone.find_all("br"):
                    br.replace_with("\n")
                dd_raw = dd_clone.get_text(separator="", strip=False)

                # サロゲート除去のみ（escape はしない）
                dd_safe = safe_utf8(dd_raw)

                color = "#000" if "◆" in dt_text else "#666"
                post_html = (
                    f'<div class="res-block" id="res{index}" style="color:{color};">'
                    f"<strong>{dt_text}</strong><br><pre>{dd_safe}</pre></div>"
                )
                posts.append(post_html)

            all_posts_html = "\n".join(posts)

            # ざっくり高さ（投稿数で増やす）
            height = min(5000, 400 + 22 * max(1, len(posts)))

            components.html(f"""
            <html>
            <head>
            <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=10, user-scalable=yes">
            <style>
            @font-face {{
                font-family: 'AAFont';
                src: url(data:font/woff2;base64,{font_base64}) format('woff2');
                font-weight: normal;
                font-style: normal;
                font-display: swap;
            }}
            body {{
                margin: 0;
                padding: 5px;
                font-family: {'AAFont, ' if font_base64 else ''}monospace;
            }}
            pre {{
                font-family: {'AAFont, ' if font_base64 else ''}monospace;
                font-size: 15px;
                line-height: 1.15;
                white-space: pre;
                overflow-x: auto;
                margin: 0;
            }}
            .res-block {{
                background-color: transparent;
                border: none;
                padding: 0;
                margin-bottom: 1.2em;
            }}
            </style>
            </head>
            <body>
            {all_posts_html}
            </body>
            </html>
            """, height=height, scrolling=True)

        except requests.exceptions.MissingSchema:
            st.error("URLが正しくありません。http:// または https:// から始めてください。")
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {str(e)}")
