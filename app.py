import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
import base64
import os
import re

st.set_page_config(layout="wide")

# カスタムフォントCSS（MS UI Gothic）
font_path = os.path.join("static", "MS-UIGothic.woff2")
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode("utf-8")

    font_css = f"""
    <style>
    @font-face {{
        font-family: 'AAFont';
        src: url("data:font/woff2;base64,{font_base64}") format('woff2');
        font-weight: normal;
        font-style: normal;
    }}

    html, body, .stApp {{
        font-family: 'AAFont', monospace;
        font-size: 14px;
        line-height: 1.4;
        background-color: #fdfdfd;
        overflow-x: auto;
    }}

    pre {{
        white-space: pre;
        overflow-x: auto;
    }}

    .gray {{
        color: #666;
    }}

    .normal {{
        color: black;
    }}

    /* 追加：レス枠の装飾を除去 */
    .res-block {{
        background-color: transparent;
        border: none;
        padding: 0;
        margin-bottom: 1.2em;
    }}
    </style>
    """
    st.markdown(font_css, unsafe_allow_html=True)
else:
    st.warning("フォントが見つかりません。static/MS-UIGothic.woff2 を確認してください。")

st.title("AA Viewer")

url = st.text_input("AAページのURLを入力してください（http:// または https://）", "")

# アンカーリンクをHTMLで埋め込む関数
def convert_anchors(text):
    return re.sub(r'&gt;&gt;(\d+)', r'<a href="#res\1" style="color:blue; text-decoration:none;">&gt;&gt;\1</a>', text)

# 読み込み処理
if st.button("読み込む"):
    if url.strip() == "":
        st.warning("URLを入力してください。")
    else:
        try:
            def normalize_url(input_url: str) -> str:
                if not re.match(r'^https?://', input_url):
                    return 'http://' + input_url
                return input_url

            normalized_url = normalize_url(url)
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(normalized_url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            dt_blocks = soup.find_all("dt")
            dd_blocks = soup.find_all("dd")

            posts = []
            for index, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
                dt_text = dt.get_text(strip=True)
                dd_raw = dd.get_text("\n")
                dd_escaped = html.escape(dd_raw)
                dd_escaped = convert_anchors(dd_escaped)
                color = "#000" if "◆" in dt_text else "#666"
                post_html = f'<div class="res-block" id="res{index}" style="color:{color};"><strong>{dt_text}</strong><br><pre>{dd_escaped}</pre></div>'
                posts.append(post_html)

            all_posts_html = "\n".join(posts)

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
                font-family: 'AAFont';
            }}
            pre {{
                font-family: 'AAFont';
                font-size: 15px;
                line-height: 1.15;
                white-space: pre;
                overflow-x: auto;
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
            """, height=3000, scrolling=True)

        except requests.exceptions.MissingSchema:
            st.error("URLが正しくありません。http:// または https:// から始めてください。")
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {str(e)}")
