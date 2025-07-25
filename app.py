import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
import base64
import os

st.set_page_config(layout="wide")
st.title("やる夫スレ AAビューア")

url = st.text_input("AAスレのURLを入力してください：")

# 「読み込む」ボタンが押されたとき、かつURLが有効なときのみ処理する
if st.button("読み込む"):
    if url.strip() == "":
        st.warning("URLを入力してください。")
    elif not url.startswith("http"):
        st.error("URLが不正です。httpまたはhttpsで始めてください。")
    else:
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # <pre> タグのテキスト抽出（複数ある場合は連結）
            aa_blocks = soup.find_all("pre")
            aa_text = "\n\n".join(block.get_text() for block in aa_blocks)

            # 表示
            st.text_area("取得したAA", aa_text, height=400)
        
        except Exception as e:
            st.error(f"読み込み失敗：{e}")

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