import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
import base64
import os

st.set_page_config(layout="wide")
st.title("やる夫スレ 完全AA対応ビューア")

# ▼ AA取得対象URL
yaruo_url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
st.write(f"読み込み対象URL：{yaruo_url}")

# ▼ HTML取得と解析
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(yaruo_url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

# ▼ <dd>タグを抽出しテキスト整形
dd_blocks = soup.find_all("dd")
aa_blocks = [html.unescape(dd.get_text("\n")) for dd in dd_blocks]
full_text = "\n\n".join(aa_blocks)

# ▼ .woff2フォント読み込み＆Base64エンコード
font_path = os.path.join("static", "MS-UIGothic.woff2")
with open(font_path, "rb") as font_file:
    woff2_base64 = base64.b64encode(font_file.read()).decode("utf-8")

# ▼ AA表示コンポーネント
components.html(f"""
<html>
<head>
<style>
@font-face {{
    font-family: 'AAFont';
    src: url(data:font/woff2;charset=utf-8;base64,{woff2_base64}) format('woff2');
    font-weight: normal;
    font-style: normal;
    font-display: swap;
}}

body {{
    background-color: #fdfdfd;
    padding: 20px;
}}

pre {{
    font-family: 'AAFont', monospace;
    font-size: 15px;
    line-height: 1.1;
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