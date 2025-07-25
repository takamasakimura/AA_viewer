import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
import base64
import os

# ページ設定
st.set_page_config(layout="wide")
st.title("やる夫スレ AAビューア（MS UI Gothic強制）")

# URL
url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
st.write(f"読み込み対象URL：{url}")

# HTML取得
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")
dd_blocks = soup.find_all("dd")
aa_blocks = [html.unescape(dd.get_text("\n")) for dd in dd_blocks]
full_text = "\n\n".join(aa_blocks)

# フォント読み込み → base64化
font_path = os.path.join("static", "MS-UIGothic.woff2")
with open(font_path, "rb") as f:
    font_data = f.read()
    font_base64 = base64.b64encode(font_data).decode("utf-8")

# 埋め込みHTML表示
components.html(f"""
<html>
<head>
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
    padding: 1rem;
    background-color: #fdfdfd;
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
    color: black;
}}
</style>
</head>
<body>
<pre>{full_text}</pre>
</body>
</html>
""", height=2400, scrolling=True)