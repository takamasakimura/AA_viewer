# app.py — AA Viewer 軽量版（◆と直後のみ表示オプション付き／モバイル対策）

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import re
import html
from copy import copy

# --- 文字サニタイズ ---
def safe_utf8(s: str) -> str:
    # サロゲート(D800–DFFF)を   に置換
    return re.sub(r'[\ud800-\udfff]', '\uFFFD', s)

def strip_controls(s: str) -> str:
    # 制御文字(C0)のうち \t \n \r 以外は   に置換
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '\uFFFD', s)

st.set_page_config(layout="wide")

# --- グローバルCSS：等幅システムフォントに統一 ---
st.markdown("""
<style>
html, body, .stApp {
  font-family: monospace;
  font-size: 14px;
  line-height: 1.4;
  background:#fdfdfd;
  overflow-x:auto;
}
pre {
  white-space: pre;
  overflow-x:auto;
  margin:0;
}
.res-block {
  background:transparent;
  border:none;
  padding:0;
  margin-bottom:1.2em;
}
.res-block.op {
  border-left:4px solid #000;
  padding-left:6px;
}
.res-block.op-follow {
  background:rgba(10,88,202,0.06);
  border-left:4px solid #0a58ca;
  padding-left:6px;
}
</style>
""", unsafe_allow_html=True)

# --- 履歴 ---
if "url_history" not in st.session_state:
    st.session_state["url_history"] = []

st.title("AA Viewer")

# フィルタ切り替え
filter_mode = st.checkbox("◆と直後のみ表示（雑談を省く）", value=True)

# 最大表示レス数をユーザー側で調整できるようにする
max_posts = st.number_input(
    "最大表示レス数（多すぎるとスマホで落ちることがあります）",
    min_value=50,
    max_value=2000,
    value=400,
    step=50,
)

st.markdown("#### 🔄 過去のURL履歴")
for old_url in reversed(st.session_state["url_history"]):
    if st.button(old_url, key=f"hist_{old_url}"):
        st.session_state["url"] = old_url

def normalize_url(u: str) -> str:
    return u if re.match(r'^https?://', u) else 'http://' + u

url = st.text_input("AAページのURLを入力してください（http:// または https://）", key="url")

# --- 読み込み ---
if st.button("読み込む"):
    if not url.strip():
        st.warning("URLを入力してください。")
    elif not (url.startswith("http://") or url.startswith("https://")):
        st.error("URLは http:// または https:// で始めてください。")
    else:
        # 履歴更新
        hist = st.session_state["url_history"]
        if url in hist:
            hist.remove(url)
        hist.append(url)
        if len(hist) > 5:
            hist.pop(0)

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(normalize_url(url), headers=headers, timeout=10)
            decoded = resp.content.decode("cp932", errors="replace")
            soup = BeautifulSoup(decoded, "html.parser")

            dt_blocks = soup.find_all("dt")
            dd_blocks = soup.find_all("dd")

            posts = []
            last_was_op = False

            for idx, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
                # 見出し
                dt_text = strip_controls(safe_utf8(dt.get_text(strip=True)))
                dt_show = html.escape(dt_text, quote=False)

                # 本文：<br> を改行に、他は改行を入れない
                dd_clone = copy(dd)
                for br in dd_clone.find_all("br"):
                    br.replace_with("\n")
                dd_raw = dd_clone.get_text(separator="", strip=False)

                dd_safe = strip_controls(safe_utf8(dd_raw))
                dd_show = html.escape(dd_safe, quote=False)

                # ◆と直後フィルタ
                is_op = ("◆" in dt_text)
                after_op = last_was_op
                last_was_op = is_op

                if filter_mode and not (is_op or after_op):
                    continue

                if is_op:
                    color = "#000"
                    role_class = "op"
                elif after_op:
                    color = "#0a58ca"
                    role_class = "op-follow"
                else:
                    color = "#666"
                    role_class = "other"

                posts.append(
                    f'<div class="res-block {role_class}" id="res{idx}" '
                    f'style="color:{color};">'
                    f"<strong>{dt_show}</strong><br><pre>{dd_show}</pre></div>"
                )

            if len(posts) == 0:
                st.info("条件に合致するレスがありませんでした。フィルタ設定を確認してください。")
                st.stop()

            # レス数が多すぎる場合は先頭 max_posts 件だけに制限
            safe_max = int(max_posts)
            if len(posts) > safe_max:
                st.info(f"レス数が多いため、先頭 {safe_max} 件まで表示しています。")
                posts = posts[:safe_max]

            all_posts_html = "\n".join(posts)
            height = min(5000, 400 + 22 * max(1, len(posts)))

            # 軽量な HTML 断片だけを埋め込む（フル <html> / <head> は使わない）
            components.html(f"""
<style>
#aa-root {{
  margin:0;
  padding:5px;
  font-family: monospace;
}}
#aa-root pre {{
  font-family: monospace;
  font-size:15px;
  line-height:1.15;
  white-space:pre;
  overflow-x:auto;
  margin:0;
}}
#aa-root .res-block {{
  background:transparent;
  border:none;
  padding:0;
  margin-bottom:1.2em;
}}
#aa-root .res-block.op {{
  border-left:4px solid #000;
  padding-left:6px;
}}
#aa-root .res-block.op-follow {{
  background:rgba(10,88,202,0.06);
  border-left:4px solid #0a58ca;
  padding-left:6px;
}}
</style>
<div id="aa-root">
{all_posts_html}
</div>
""", height=height, scrolling=True)

        except requests.exceptions.MissingSchema:
            st.error("URLが正しくありません。http:// または https:// で始めてください。")
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {str(e)}")
