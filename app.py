# aa_viewer.py
import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(layout="wide")
st.title("やる夫スレ AA ビューア（スマホ対応）")

url = st.text_input("対象URLを入力してください", "http://yaruoshelter.com/yaruo001/kako/1476/14766/1476693021.html")

if st.button("読み込む"):
    try:
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # AAと思われる部分の抽出（例：<blockquote>タグ内）
        blocks = soup.find_all("blockquote")

        st.markdown("---")
        st.subheader("抽出されたAA：")

        for block in blocks:
            text = block.get_text()
            # 改行保持＋等幅フォント＋スクロール対応
            st.markdown(
                f"""
                <div style="
                    font-family: 'Courier New', Courier, monospace;
                    white-space: pre;
                    overflow-x: auto;
                    background-color: #f5f5f5;
                    padding: 1em;
                    margin-bottom: 1em;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                ">
                {text}
                </div>
                """,
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"取得に失敗しました：{e}")