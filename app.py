import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
import base64
import os

st.set_page_config(layout="wide")

# カスタムCSS（MSPゴシック + フォント設定）
font_path = os.path.join("static", "MS-UIGothic.woff2")
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_data = f.read()
        font_base64 = font_data.encode("base64").decode("utf-8") if hasattr(font_data, "encode") else font_data.encode("base64")

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
    </style>
    """
    st.markdown(font_css, unsafe_allow_html=True)
else:
    st.warning("フォントが見つかりません。static/MS-UIGothic.woff2 を確認してください。")

st.title("やる夫スレ AAビューア")

url = st.text_input("AAスレのURLを入力してください：")

# 読み込みを試みるのは「ボタンが押されたとき」かつ「URLが有効なとき」
if url:
    if st.button("読み込む"):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            posts = soup.find_all("pre")
            if not posts:
                st.warning("AAを含む <pre> タグが見つかりませんでした。")
            else:
                for i, post in enumerate(posts):
                    text = post.get_text()
                    if "◆" in text:
                        st.markdown(f"<pre class='normal'>{text}</pre>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<pre class='gray'>{text}</pre>", unsafe_allow_html=True)

        except requests.exceptions.MissingSchema:
            st.error("URLが正しくありません。http:// または https:// から始めてください。")
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {str(e)}")
else:
    st.info("URLを入力してください。")

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

# dat形式（<dt> = メタ情報, <dd> = 本文）
dt_blocks = soup.find_all("dt")
dd_blocks = soup.find_all("dd")

posts = []
for dt, dd in zip(dt_blocks, dd_blocks):
    dt_text = dt.get_text(strip=True)
    dd_text = html.unescape(dd.get_text("\n"))
    color = "#000" if "◆" in dt_text else "#666"
    post_html = f'<div style="color:{color}; margin-bottom:1em;"><strong>{dt_text}</strong><br><pre>{dd_text}</pre></div>'
    posts.append(post_html)

all_posts_html = "\n".join(posts)

font_path = os.path.join("static", "MS-UIGothic.woff2")
with open(font_path, "rb") as f:
    font_data = f.read()
    font_base64 = base64.b64encode(font_data).decode("utf-8")

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
    background-color: #f9f9f9;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 10px;
}}
</style>
</head>
<body>
{all_posts_html}
</body>
</html>
""", height=3000, scrolling=True)