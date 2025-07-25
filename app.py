import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
import os

st.set_page_config(layout="wide")
st.title("やる夫スレ 完全AA対応ビューア")

# 読み込むURL（ここは任意で差し替えてください）
yaruo_url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
st.write(f"読み込み対象URL：{yaruo_url}")

# ▼ HTML取得
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(yaruo_url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

# ▼ 本文の抽出
dd_blocks = soup.find_all("dd")
aa_blocks = [html.unescape(dd.get_text("\n")) for dd in dd_blocks]
full_text = "\n\n".join(aa_blocks)

# ▼ static フォルダのローカルパスを取得
font_path = os.path.join("static", "MS-PGothic.woff2")

# ▼ HTMLとCSS（font-face指定とAA描画）
components.html(f"""
<html>
<head>
<style>
@font-face {{
  font-family: 'AAFont';
  src: url(data:font/woff2;base64,{woff2_base64}) format('woff2');
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}
pre {{
  font-family: 'AAFont', monospace;
  font-size: 15px;
  ...
}}
</style>
</head>
<body>
<pre>{full_text}</pre>
</body>
</html>
""", height=2400, scrolling=True)