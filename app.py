# app.py — AA Viewer + Textar-light Webフォント版 + 簡易フルスクリーンモード
# ・◆と直後のみ表示フィルタ
# ・ページ範囲指定 / 全レス表示
# ・ttp://, yaruo～.html などのURL補正
# ・Textar-light WebフォントをCSSで直接指定
# ・横画面向け「簡易全画面モード」でStreamlitのヘッダー類を隠す

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import re
import html
from copy import copy

# 全レスモード時の安全上限
HARD_MAX_ALL = 3000

# ------------------------------------------------------------
# 文字サニタイズ
# ------------------------------------------------------------

def safe_utf8(s: str) -> str:
    """サロゲートペアの片割れなどを   に置換する"""
    return re.sub(r'[\ud800-\udfff]', '\uFFFD', s)

def strip_controls(s: str) -> str:
    """制御文字のうち \t \n \r 以外を   に置換する"""
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '\uFFFD', s)

# ------------------------------------------------------------
# URL 補正
# ------------------------------------------------------------

def normalize_url(raw: str) -> str:
    """
    入力文字列を「requestsが解釈できるURL」に寄せる。

    - 先頭 ttp:// → http://
    - 先頭 ttps:// → https://
    - それでも http(s) で始まっていない場合、
      .html で終わる or '.' を含むなら http:// を前に付ける
    """
    u = raw.strip()

    # ttp / ttps 補正
    if u.startswith("ttp://"):
        u = "h" + u          # → http://
    elif u.startswith("ttps://"):
        u = "h" + u          # → https://

    # すでに http(s)
    if re.match(r"^https?://", u, re.IGNORECASE):
        return u

    # ドメインぽい / .html で終わる
    if u.endswith(".html") or "." in u:
        return "http://" + u

    # それ以外はそのまま返す（後続で MissingSchema などの例外になる）
    return u

# ------------------------------------------------------------
# Streamlit 基本設定
# ------------------------------------------------------------

st.set_page_config(layout="wide")

# メイン側の軽いCSS（AA本体は iframe 内で別途指定）
st.markdown(
    """
<style>
html, body, .stApp {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
               "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.4;
  background:#fdfdfd;
  overflow-x:auto;
}
pre {
  white-space: pre;
  overflow-x: auto;
  margin: 0;
}
.res-block {
  background: transparent;
  border: none;
  padding: 0;
  margin-bottom: 1.2em;
}
.res-block.op {
  border-left: 4px solid #000;
  padding-left: 6px;
}
.res-block.op-follow {
  background: rgba(10,88,202,0.06);
  border-left: 4px solid #0a58ca;
  padding-left: 6px;
}
</style>
""",
    unsafe_allow_html=True,
)

# 履歴
if "url_history" not in st.session_state:
    st.session_state["url_history"] = []

st.title("AA Viewer（Textar-light 対応）")

# ------------------------------------------------------------
# 簡易フルスクリーンモード（ヘッダー等を隠す）
# ------------------------------------------------------------

fullscreen = st.checkbox(
    "横画面用・簡易全画面モード（Streamlitのヘッダー/フッターを隠す）",
    value=False,
    help="ON にするとヘッダーやフッター、ツールバーを隠してAA表示を広くします。",
)

if fullscreen:
    # Streamlit のヘッダー / フッター / ツールバーをCSSで非表示
    st.markdown(
        """
<style>
header[data-testid="stHeader"] {display: none;}
footer[data-testid="stFooter"] {display: none;}
div[data-testid="stToolbar"] {display: none;}
#MainMenu {visibility: hidden;}
/* 余白を詰めてAAの表示エリアを広げる */
.block-container {
  padding-top: 0.2rem;
  padding-bottom: 0.2rem;
  padding-left: 0.2rem;
  padding-right: 0.2rem;
}
</style>
""",
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# 上部コントロール
# ------------------------------------------------------------

# ◆と直後のみ表示
filter_mode = st.checkbox("◆と直後のみ表示（雑談を省く）", value=True)

# 1ページあたりのレス数
page_size = st.number_input(
    "1ページあたりのレス数（多すぎるとスマホで落ちることがあります）",
    min_value=50,
    max_value=2000,
    value=400,
    step=50,
)

# 全レス表示
all_mode = st.checkbox(
    "全レス表示（レス数が多いときはスマホで落ちる可能性があります）",
    value=False,
)

# 範囲指定開始レス（全レス表示ON時は無視）
start_no = st.number_input(
    "表示開始レス番号（例: 1 → 1～400, 401 → 401～800）※全レス表示ONのときは無視されます",
    min_value=1,
    value=1,
    step=int(page_size),
)

# Textar-light Webフォントを使うか
use_textar_font = st.checkbox(
    "Textar Webフォント（textar-light）を使う",
    value=True,
    help="ON: textar-light Webフォントを読み込んでAAを表示（外部サイトのフォントを利用します）",
)

st.markdown("#### 🔄 過去のURL履歴")
for old_url in reversed(st.session_state["url_history"]):
    if st.button(old_url, key=f"hist_{old_url}"):
        st.session_state["url"] = old_url

# URL 入力
raw_url_input = st.text_input(
    "AAページのURL（http://, https://, ttp://, yaruo～.html など）を入力してください",
    key="url",
)

# ------------------------------------------------------------
# 「読み込む」ボタン
# ------------------------------------------------------------

if st.button("読み込む"):
    raw_url = (raw_url_input or "").strip()

    if not raw_url:
        st.warning("URLを入力してください。")
    else:
        # URL 補正
        url = normalize_url(raw_url)

        st.caption(f"実際にアクセスしようとしているURL: {url}")

        # 履歴更新（生の入力文字列を保存）
        hist = st.session_state["url_history"]
        if raw_url in hist:
            hist.remove(raw_url)
        hist.append(raw_url)
        if len(hist) > 5:
            hist.pop(0)

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            decoded = resp.content.decode("cp932", errors="replace")
            soup = BeautifulSoup(decoded, "html.parser")

            dt_blocks = soup.find_all("dt")
            dd_blocks = soup.find_all("dd")

            total_raw = len(dt_blocks)

            filtered_posts = []
            last_was_op = False

            # ------------------------------------------------
            # dt/dd からレスを組み立て
            # ------------------------------------------------
            for idx, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
                # 見出し
                dt_text = strip_controls(safe_utf8(dt.get_text(strip=True)))
                dt_show = html.escape(dt_text, quote=False)

                # 本文：<br> を改行に変換
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
                    color = "#000000"
                    role_class = "op"
                elif after_op:
                    color = "#0a58ca"
                    role_class = "op-follow"
                else:
                    color = "#666666"
                    role_class = "other"

                html_block = (
                    f'<div class="res-block {role_class}" id="res{idx}" '
                    f'style="color:{color};">'
                    f"<strong>{dt_show}</strong><br>"
                    f"<pre>{dd_show}</pre></div>"
                )
                filtered_posts.append((idx, html_block))

            if len(filtered_posts) == 0:
                st.info("条件に合致するレスがありませんでした。フィルタ設定を確認してください。")
                st.stop()

            safe_start = int(start_no)
            safe_page = int(page_size)

            # ------------------------------------------------
            # ページング / 全レス
            # ------------------------------------------------
            if all_mode:
                page_posts = filtered_posts
                if len(page_posts) > HARD_MAX_ALL:
                    st.info(
                        f"全レス表示モードですが、負荷対策のため先頭 {HARD_MAX_ALL} 件までに制限しています。"
                    )
                    page_posts = page_posts[:HARD_MAX_ALL]
                caption_range = "全レス表示"
            else:
                range_start = safe_start
                range_end = safe_start + safe_page - 1
                page_posts = [
                    (idx, html_block)
                    for idx, html_block in filtered_posts
                    if range_start <= idx <= range_end
                ]
                caption_range = f"{range_start}～{range_end}"

            st.caption(
                f"スレ全体のレス数: {total_raw} / フィルタ後: {len(filtered_posts)} "
                f"｜ 表示範囲: {caption_range}"
            )

            if not page_posts:
                st.info("指定された範囲には表示するレスがありませんでした。")
                st.stop()

            page_posts_html = [html_block for _, html_block in page_posts]
            all_posts_html = "\n".join(page_posts_html)

            # フルスクリーン時はちょっとだけ上限を緩める
            max_height = 6000 if fullscreen else 5000
            height = min(max_height, 400 + 22 * max(1, len(page_posts_html)))

            # ------------------------------------------------
            # AA 埋め込み用 HTML + CSS（ここでフォント指定）
            # ------------------------------------------------
            if use_textar_font:
                # marmooo さんの Textar-light 向けCSSをベースにした設定
                font_face_css = """
@font-face {
  font-family: 'Textar';
  font-style: normal;
  font-weight: normal;
  src: local('Textar'),
       url('https
