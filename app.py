import streamlit as st
import requests
from bs4 import BeautifulSoup
import html

st.set_page_config(layout="wide")
st.title("やる夫スレ 全文AAビューア（等幅表示・地の文あり）")

url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
st.write(f"読み込み対象URL：{url}")

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

# <dd> すべてをプレーンテキストとして結合
dd_blocks = soup.find_all("dd")
all_text = []

for dd in dd_blocks:
    # HTMLエスケープを元に戻す（&nbsp; → 半角スペースなど）
    raw = html.unescape(dd.get_text("\n"))
    all_text.append(raw)

combined_text = "\n\n".join(all_text)

# スタイルつきで全文表示
st.markdown(
    f"""
    <div style="
        font-family: 'MS PGothic', 'MS Gothic', 'Osaka-mono', 'Courier New', Courier, monospace;
        font-size: 15px;
        line-height: 1.15;
        white-space: pre;
        overflow-x: auto;
        background-color: #fefefe;
        padding: 1em;
        border: 1px solid #ccc;
        border-radius: 6px;
    ">
    {combined_text}
    </div>
    """,
    unsafe_allow_html=True
)