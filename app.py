# app.py — AA Viewer ページ範囲＋全レス表示＋AA専用フォントオプション付き

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import re
import html
from copy import copy
import os
import base64

# 全レスモード時の安全上限（これ以上は自動で切り捨て）
HARD_MAX_ALL = 3000

# --- 文字サニタイズ ---
def safe_utf8(s: str) -> str:
    # サロゲート(D800–DFFF)を   に置換
    return re.sub(r'[\ud800-\udfff]', '\uFFFD', s)

def strip_controls(s: str) -> str:
    # 制御文字(C0)のうち \t \n \r 以外は   に置換
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '\uFFFD', s)

# --- URL 補正 ---
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

    # ttp / ttps を補正
    if u.startswith("ttp://"):
        u = "h" + u  # → http://
    elif u.startswith("ttps://"):
        u = "h" + u  # → https://

    # すでに http(s) ならそのまま
    if re.match(r"^https?://", u, re.IGNORECASE):
        return u

    # それ以外で .html で終わる or ドメインっぽく '.' を含んでいる場合は、
    # 'http://' を付けてみる（例: yaruo.sakura.ne.jp/aaa.html）
    if u.endswith(".html") or "." in u:
        return "http://" + u

    # ここまで来たら、URLとしてはかなり曖昧なのでそのまま返す
    # → 後続の requests.get で MissingSchema / InvalidURL が出る
    return u

st.set_page_config(layout="wide")

# --- AA専用フォント（static/MS-UIGothic.woff2）を読み込み（あれば） ---
AA_FONT_CSS_SNIPPET = ""
font_path = os.path.join("static", "MS-UIGothic.woff2")
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = base64.b64encode(f.read()).decode("utf-8")
        # 後で <style> 内にそのまま差し込む用の CSS スニペット
        AA_FONT_CSS_SNIPPET = (
            "@font-face {\n"
            "  font-family: 'AAFont';\n"
            f"  src: url(\"data:font/woff2;base64,{font_data}\") format('woff2');\n"
            "  font-display: swap;\n"
            "}\n"
        )
    except Exception:
        AA_FONT_CSS_SNIPPET = ""

# --- グローバルCSS：等幅システムフォントに統一（AA部分はあとで上書き） ---
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

# AA専用フォントを使うか（フォントファイルがある場合だけ有効）
use_aa_font = False
if AA_FONT_CSS_SNIPPET:
    use_aa_font = st.checkbox(
        "AA専用フォント（ずれ補正・やや重め）を使う",
        value=True,
    )
else:
    st.caption(
        "AA専用フォント (static/MS-UIGothic.woff2) が見つからないため、"
        "システム標準フォントで表示しています。"
    )

st.markdown("#### 🔄 過去のURL履歴")
for old_url in reversed(st.session_state["url_history"]):
    if st.button(old_url, key=f"hist_{old_url}"):
        st.session_state["url"] = old_url

# ユーザー入力
raw_url_input = st.text_input(
    "AAページのURL（http://, https://, ttp://, yaruo～.html など）を入力してください",
    key="url",
)

# --- 読み込み ---
if st.button("読み込む"):
    raw_url = (raw_url_input or "").strip()

    if not raw_url:
        st.warning("URLを入力してください。")
    else:
        # URL を補正
        url = normalize_url(raw_url)

        # 補正結果を軽く表示（デバッグ兼ねて）
        st.caption(f"実際にアクセスしようとしているURL: {url}")

        # 履歴更新（生の入力文字列を保存しておく）
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

            page_posts_html = [html_block for _, html_block in page_posts]
            all_posts_html = "\n".join(page_posts_html)
            height = min(5000, 400 + 22 * max(1, len(page_posts_html)))

            # AA専用フォントを使うかどうかで CSS を出し分け
            font_face_css = AA_FONT_CSS_SNIPPET if (use_aa_font and AA_FONT_CSS_SNIPPET) else ""
            font_family_css = "'AAFont', monospace" if (use_aa_font and AA_FONT_CSS_SNIPPET) else "monospace"

            # 軽量な HTML 断片だけを埋め込む
            components.html(
                f"""
<style>
{font_face_css}
#aa-root {{
  margin:0;
  padding:5px;
  font-family: {font_family_css};
}}
#aa-root pre {{
  font-family: {font_family_css};
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
