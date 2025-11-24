# app.py — AA Viewer + Textar Font 対応版
# ・やる夫 AA 用 Textar フォント（textar-font-wrapper）に対応
# ・◆と直後のみ表示フィルタ
# ・ページ範囲指定 / 全レス表示
# ・ttp:// や yaruo～.html もある程度補正して読みに行く

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import re
import html
from copy import copy

# 全レスモード時の安全上限（これ以上は自動で切り捨て）
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
    入力された文字列を「requests でアクセス可能な URL」に寄せていく関数。

    主な補正:
      - 先頭が ttp:// → http:// に補正
      - 先頭が ttps:// → https:// に補正
      - それでも http(s) で始まっていない場合、
        .html で終わる or '.' を含むなら 'http://' を前に付ける
    """
    u = raw.strip()

    # ttp / ttps 補正
    if u.startswith("ttp://"):
        u = "h" + u           # → http://
    elif u.startswith("ttps://"):
        u = "h" + u           # → https://

    # すでに http(s) ならそのまま
    if re.match(r"^https?://", u, re.IGNORECASE):
        return u

    # .html で終わる or ドメインっぽく '.' を含む → http:// を補ってみる
    if u.endswith(".html") or "." in u:
        return "http://" + u

    # ここまで来たらかなり曖昧なので、そのまま返す
    # → 後続の requests.get で MissingSchema / InvalidURL になる
    return u

# ------------------------------------------------------------
# Streamlit UI 基本設定
# ------------------------------------------------------------

st.set_page_config(layout="wide")

# グローバル CSS（ここではフォントファミリは固定しない）
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

# 履歴保存
if "url_history" not in st.session_state:
    st.session_state["url_history"] = []

st.title("AA Viewer（Textar Font 対応）")

# ------------------------------------------------------------
# 上部コントロール
# ------------------------------------------------------------

# ◆とその直後のみ表示
filter_mode = st.checkbox("◆と直後のみ表示（雑談を省く）", value=True)

# 1ページあたりのレス数
page_size = st.number_input(
    "1ページあたりのレス数（多すぎるとスマホで落ちることがあります）",
    min_value=50,
    max_value=2000,
    value=400,
    step=50,
)

# 全レス表示モード
all_mode = st.checkbox(
    "全レス表示（レス数が多いときはスマホで落ちる可能性があります）",
    value=False,
)

# 範囲指定用の開始レス番号（全レス表示ON時は無視）
start_no = st.number_input(
    "表示開始レス番号（例: 1 → 1～400, 401 → 401～800）※全レス表示ONのときは無視されます",
    min_value=1,
    value=1,
    step=int(page_size),
)

# Textar フォントを使うかどうか
use_textar_font = st.checkbox(
    "Textar Font（やる夫 AA 用フォント）を使う",
    value=True,
    help="ON にすると textar-font-wrapper の Web フォントを使って AA を表示します。",
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
# 「読み込む」ボタン押下時の処理
# ------------------------------------------------------------

if st.button("読み込む"):
    raw_url = (raw_url_input or "").strip()

    if not raw_url:
        st.warning("URLを入力してください。")
    else:
        # URL を補正
        url = normalize_url(raw_url)

        # 実際に取りに行く URL を表示
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

            # フィルタ後レス（(元レス番号, html文字列)）
            filtered_posts = []
            last_was_op = False

            for idx, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
                # 見出しテキスト
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

                # Textar フォント用クラスを pre につける
                pre_class = "textar-aa"

                html_block = (
                    f'<div class="res-block {role_class}" id="res{idx}" '
                    f'style="color:{color};">'
                    f"<strong>{dt_show}</strong><br>"
                    f'<pre class="{pre_class}">{dd_show}</pre></div>'
                )
                filtered_posts.append((idx, html_block))

            if len(filtered_posts) == 0:
                st.info("条件に合致するレスがありませんでした。フィルタ設定を確認してください。")
                st.stop()

            safe_start = int(start_no)
            safe_page = int(page_size)

            # ページング／全レス
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

            # 情報表示
            st.caption(
                f"スレ全体のレス数: {total_raw} / フィルタ後: {len(filtered_posts)} "
                f"｜ 表示範囲: {caption_range}"
            )

            if not page_posts:
                st.info("指定された範囲には表示するレスがありませんでした。")
                st.stop()

            # HTML 連結
            page_posts_html = [html_block for _, html_block in page_posts]
            all_posts_html = "\n".join(page_posts_html)
            height = min(5000, 400 + 22 * max(1, len(page_posts_html)))

            # Textar フォントの script タグ（ON のときだけ出力）
            textar_script = ""
            if use_textar_font:
                # ローカルに textar-font を置いた場合は下の URL を
                #   "/static/textar-font/webfont.js"
                # に変える
                textar_script = (
                    '<script type="text/javascript" charset="utf-8" '
                    'src="/static/textar-font/webfont.js"></script>'
                )

            # 埋め込み HTML
            components.html(
                f"""
<style>
#aa-root {{
  margin: 0;
  padding: 5px;
}}
#aa-root pre {{
  /* フォントファミリは指定しない（Textar 側の .textar-aa に任せる） */
  font-size: 15px;
  line-height: 1.15;
  white-space: pre;
  overflow-x: auto;
  margin: 0;
}}
#aa-root .res-block {{
  background: transparent;
  border: none;
  padding: 0;
  margin-bottom: 1.2em;
}}
#aa-root .res-block.op {{
  border-left: 4px solid #000;
  padding-left: 6px;
}}
#aa-root .res-block.op-follow {{
  background: rgba(10,88,202,0.06);
  border-left: 4px solid #0a58ca;
  padding-left: 6px;
}}
</style>
{textar_script}
<div id="aa-root">
{all_posts_html}
</div>
""",
                height=height,
                scrolling=True,
            )

        except requests.exceptions.MissingSchema:
            st.error(
                "URLの形式を解釈できませんでした。\n"
                "http:// または https:// から始まる完全なURL、もしくは ttp:// 形式に近い文字列を入力してください。"
            )
        except requests.exceptions.RequestException as e:
            st.error(
                f"URLに接続できませんでした: {e}\n"
                "入力した文字列が実際にウェブ上で開けるURLか確認してみてください。"
            )
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {str(e)}")
