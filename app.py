import streamlit as st
import requests
from bs4 import BeautifulSoup
import html

st.set_page_config(layout="wide")
st.title("やる夫スレ AAビューア（スマホ対応・DD抽出対応）")

url = "http://yaruoshelter.com/yaruo001/kako/1542/15429/1542970809.html"
st.write(f"読み込み対象URL：{url}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    st.info("HTML取得中…")
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")

    # レスの本体は <dd> にある（AA含む）
    dd_blocks = soup.find_all("dd")
    st.success(f"{len(dd_blocks)} 件のレスを検出しました。")

    # ページャー
    per_page = 30
    total_pages = (len(dd_blocks) - 1) // per_page + 1

    if "page" not in st.session_state:
        st.session_state.page = 0

    page = st.slider("表示するページ", 0, total_pages - 1, st.session_state.page)
    st.session_state.page = page

    start = page * per_page
    end = start + per_page

    st.markdown("---")
    for i, dd in enumerate(dd_blocks[start:end], start=start):
        html_raw = str(dd)
        soup_inner = BeautifulSoup(html_raw, "html.parser")
        for tag in soup_inner.find_all(["font", "b"]):
            tag.unwrap()
        text = soup_inner.get_text("\n")
        text = html.unescape(text)

        st.markdown(
            f"""
            <div style="
                font-family: 'MS PGothic', 'MS Gothic', 'Osaka-mono', 'Courier New', Courier, monospace;
                font-size: 15px;
                line-height: 1.15;
                white-space: pre;
                overflow-x: auto;
                background-color: #f9f9f9;
                padding: 0.7em;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-bottom: 1.2em;
            ">
            <span style="color: gray; font-size: 0.8em;">レス {i}</span><br>
            {text}
            </div>
            """,
            unsafe_allow_html=True
        )

except Exception as e:
    st.error(f"読み込みに失敗しました: {e}")