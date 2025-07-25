import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("やる夫スレ 完全AA対応ビューア")


# ▼ 1. 修正点①: URL先のHTML全文取得
yaruo_url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
st.write(f"読み込み対象URL：{yaruo_url}")

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(yaruo_url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

# ▼ 2. 修正点②: <dd>タグ内のテキスト（本文＋AA）を一括抽出
dd_blocks = soup.find_all("dd")
aa_blocks = [html.unescape(dd.get_text("\n")) for dd in dd_blocks]
full_text = "\n\n".join(aa_blocks)

# ▼ 3. 修正点③: <pre>タグ + CSS指定により、AAが崩れないよう等幅描画
components.html(f"""
<html>
<head>
<style>
@font-face {{
  font-family: 'AAFont';
  src: url(data:font/woff2;charset=utf-8;base64,AAEAA...) format('woff2');
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