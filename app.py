import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components
from base64 import b64encode

st.set_page_config(layout="wide")
st.title("やる夫スレ AAビューア（埋め込みフォント対応）")

# スレッドURL
url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

# <dd> の本文テキストを抽出（AA・地の文すべて）
dd_blocks = soup.find_all("dd")
full_text = "\n\n".join([html.unescape(dd.get_text("\n")) for dd in dd_blocks])

# woff2フォントを読み込んでBase64化
with open("MyricaMM.woff2", "rb") as f:
    woff2_base64 = b64encode(f.read()).decode("utf-8")

# HTML + CSSで埋め込みフォント付きAA表示
components.html(f"""
<html>
<head>
<style>
@font-face {{
  font-family: 'Myrica';
  src: url(data:font/woff2;charset=utf-8;base64,{woff2_base64}) format('woff2');
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}

pre {{
  font-family: 'Myrica', 'MyricaM M', 'SF Mono', 'Menlo', 'Consolas', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.25;
  white-space: pre;
  background-color: #f9f9f9;
  border: 1px solid #ccc;
  padding: 10px;
  overflow-x: auto;
}}
</style>
</head>
<body>

<h3>▼ フォント整列テスト</h3>
<pre>
012345678901234567890123456789
■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
</pre>

<h3>▼ AA表示（本文）</h3>
<pre>{full_text}</pre>

</body>
</html>
""", height=2400, scrolling=True)
