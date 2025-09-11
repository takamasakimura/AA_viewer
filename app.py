# app.py — AA Viewer（途切れ対策入り・最小修正）

import streamlit as st
import requests
from bs4 import BeautifulSoup
import streamlit.components.v1 as components
import base64, os, re
from copy import copy
import html

# --- 文字サニタイズ ---
def safe_utf8(s: str) -> str:
    # サロゲート(D800–DFFF) →   に
    return re.sub(r'[\ud800-\udfff]', '\uFFFD', s)

def strip_controls(s: str) -> str:
    # 制御文字(C0)のうち \t \n \r 以外は   に
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '\uFFFD', s)

st.set_page_config(layout="wide")

# --- フォント（あれば埋め込み） ---
font_base64 = ""
font_path = os.path.join("static", "MS-UIGothic.woff2")
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        pass

st.markdown(f"""
<style>
@font-face {{
  font-family: 'AAFont';
  src: url("data:font/woff2;base64,{font_base64}") format('woff2');
}}
html, body, .stApp {{
  font-family: {'AAFont, ' if font_base64 else ''}monospace;
  font-size: 14px; line-height: 1.4; background:#fdfdfd; overflow-x:auto;
}}
pre {{
  white-space: pre; overflow-x:auto; margin:0;
}}
.res-block {{ background:transparent; border:none; padding:0; margin-bottom:1.2em; }}
</style>
""", unsafe_allow_html=True)

if not font_base64:
    st.warning("フォントが見つかりません。static/MS-UIGothic.woff2 を確認してください。等幅フォントで表示します。")

# --- 履歴UI ---
if "url_history" not in st.session_state:
    st.session_state["url_history"] = []

st.title("AA Viewer")
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
        hist = st.session_state["url_history"]
        if url in hist: hist.remove(url)
        hist.append(url)
        if len(hist) > 5: hist.pop(0)

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(normalize_url(url), headers=headers, timeout=10)
            decoded = resp.content.decode("cp932", errors="replace")
            soup = BeautifulSoup(decoded, "html.parser")

            dt_blocks = soup.find_all("dt")
            dd_blocks = soup.find_all("dd")

            posts = []
            for idx, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
                # 見出し（安全化してからエスケープ）
                dt_text = strip_controls(safe_utf8(dt.get_text(strip=True)))
                dt_show = html.escape(dt_text, quote=False)

                # 本文：<br>だけ改行化、他は改行を入れない
                dd_clone = copy(dd)
                for br in dd_clone.find_all("br"):
                    br.replace_with("\n")
                dd_raw = dd_clone.get_text(separator="", strip=False)

                # 文字サニタイズ → タグ誤解釈防止のため最小エスケープ
                dd_safe = strip_controls(safe_utf8(dd_raw))
                dd_show = html.escape(dd_safe, quote=False)  # &, <, > を実体参照化

                color = "#000" if "◆" in dt_text else "#666"
                posts.append(
                    f'<div class="res-block" id="res{idx}" style="color:{color};">'
                    f"<strong>{dt_show}</strong><br><pre>{dd_show}</pre></div>"
                )

            all_posts_html = "\n".join(posts)
            height = min(5000, 400 + 22 * max(1, len(posts)))

            components.html(f"""
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=10, user-scalable=yes">
<style>
@font-face {{
  font-family: 'AAFont';
  src: url(data:font/woff2;base64,{font_base64}) format('woff2');
  font-display: swap;
}}
body {{ margin:0; padding:5px; font-family: {'AAFont, ' if font_base64 else ''}monospace; }}
pre  {{ font-family: {'AAFont, ' if font_base64 else ''}monospace; font-size:15px; line-height:1.15; white-space:pre; overflow-x:auto; margin:0; }}
.res-block {{ background:transparent; border:none; padding:0; margin-bottom:1.2em; }}
</style>
</head>
<body>
{all_posts_html}
</body>
</html>
""", height=height, scrolling=True)

        except requests.exceptions.MissingSchema:
            st.error("URLが正しくありません。http:// または https:// から始めてください。")
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {str(e)}")
