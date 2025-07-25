import streamlit as st
import requests
from bs4 import BeautifulSoup
import html
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("やる夫スレ 完全AA対応ビューア")

url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

dd_blocks = soup.find_all("dd")
aa_blocks = []

for dd in dd_blocks:
    text = html.unescape(dd.get_text("\n"))
    aa_blocks.append(text)

full_text = "\n\n".join(aa_blocks)

# HTMLで直接表示（Markdownを経由しない）
components.html(f"""
<html>
<head>
<style>
body {{
    background-color: #fdfdfd;
    padding: 20px;
}}
pre {{
    font-family: 'MS PGothic', 'MS Gothic', 'Osaka-mono', 'Courier New', Courier, monospace;
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