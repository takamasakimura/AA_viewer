# app.py — AA Viewer ページ範囲＋全レス表示モード付き（◆と直後のみ表示／モバイル対策）

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import re
import html
from copy import copy

# 安全側の全レス最大数（全レスモードでもこれ以上は切る）
HARD_MAX_ALL = 3000

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

# ◆と直後のみ表示するか
filter_mode = st.checkbox("◆と直後のみ表示（雑談を省く）", value=True)

# 1ページあたりのレス数（例: 400）
page_size = st.number_input(
    "1ページあたりのレス数（多すぎるとスマホで落ちることがあります）",
    min_value=50,
    max_value=2000,
    value=400,
    step=50,
)

# 全レス表示モード（PCなどで、負荷を覚悟して全部見たいとき用）
all_mode = st.checkbox(
    "全レス表示（レス数が多いときはスマホで落ちる可能性があります）",
    value=False,
)

# 開始レス番号（1～）を指定
start_no = st.number_input(
    "表示開始レス番号（例: 1 → 1～400, 401 → 401～800）※全レス表示ONのときは無視されます",
    min_value=1,
    value=1,
    step=int(page_size),
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

            total_raw = len(dt_blocks)

            # フィルタ済みレス一覧（(元レス番号, html文字列) のタプル）
            filtered_posts = []
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

                html_block = (
                    f'<div class="res-block {role_class}" id="res{idx}" '
                    f'style="color:{color};">'
                    f"<strong>{dt_show}</strong><br><pre>{dd_show}</pre></div>"
                )
                filtered_posts.append((idx, html_block))

            if len(filtered_posts) == 0:
                st.info("条件に合致するレスがありませんでした。フィルタ設定を確認してください。")
                st.stop()

            safe_start = int(start_no)
            safe_page = int(page_size)

            if all_mode:
                # 全レス表示モード
                page_posts = filtered_posts
                # あまりにも多いと危ないので、HARD_MAX_ALL 件を上限にする
                if len(page_posts) > HARD_MAX_ALL:
                    st.info(
                        f"全レス表示モードですが、負荷対策のため先頭 {HARD_MAX_ALL} 件までに制限しています。"
                    )
                    page_posts = page_posts[:HARD_MAX_ALL]

                caption_range = "全レス表示"
            else:
                # 範囲指定モード
                range_start = safe_start
                range_end = safe_start + safe_page - 1

                page_posts = [
                    (idx, html_block)
                    for idx, html_block in filtered_posts
                    if range_start <= idx <= range_end
                ]
                caption_range = f"{range_start}～{range_end}"

            # 情報表示（全体とフィルタ後の件数）
            st.caption(
                f"スレ全体のレス数: {total_raw} / フィルタ後: {len(filtered_posts)} "
                f"｜ 表示範囲: {caption_range}"
            )

            if not page_posts:
                st.info("指定された範囲には表示するレスがありませんでした。")
                st.stop()

            # 実際に表示するHTMLだけ取り出す
            page_posts_html = [html_block for _, html_block in page_posts]

            all_posts_html = "\n".join(page_posts_html)
            height = min(5000, 400 + 22 * max(1, len(page_posts_html)))

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
