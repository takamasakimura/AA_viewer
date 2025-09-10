import streamlit as st
import requests, base64, os, re, html
from bs4 import BeautifulSoup
from bs4 import UnicodeDammit
import streamlit.components.v1 as components

# --- session init ---
if "url_history" not in st.session_state:
    st.session_state["url_history"] = []
if "url_input" not in st.session_state:
    st.session_state["url_input"] = ""

st.set_page_config(layout="wide")
st.title("AA Viewer")

# --- history UI ---
st.markdown("#### 🔄 過去のURL履歴")
for old_url in reversed(st.session_state["url_history"]):
    if st.button(old_url, key=f"hist_{old_url}"):
        st.session_state["url_input"] = old_url
        st.rerun()

url_value = st.text_input(
    "AAページのURLを入力してください（http:// または https://）",
    key="url_input"
)

# --- optional webfont ---
font_base64 = ""
font_path = os.path.join("static", "MS-UIGothic.woff2")
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode("utf-8")
else:
    st.info("任意: static/MS-UIGothic.woff2 があればAA幅が安定します。")

def normalize_url(u: str) -> str:
    u = u.strip()
    if not re.match(r"^https?://", u):
        return "http://" + u
    return u

def fetch_html(u: str) -> str:
    """混在エンコでも落ちない安全デコード"""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(u, headers=headers, timeout=15)
    resp.raise_for_status()

    dm = UnicodeDammit(resp.content)
    text = dm.unicode_markup if dm.unicode_markup else resp.content.decode("utf-8", "replace")
    # サロゲート除去（U+D800–DFFF）
    text = re.sub(r"[\ud800-\udfff]", " ", text)
    return text

def extract_posts(doc: str) -> str:
    """<dt><dd> 形式を想定。改行・空白は壊さない"""
    soup = BeautifulSoup(doc, "html.parser")
    dt_blocks = soup.find_all("dt")
    dd_blocks = soup.find_all("dd")
    posts = []

    for idx, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
        dt_text = dt.get_text(strip=True)
        raw_html = dd.decode_contents()                         # innerHTMLをそのまま
        body = re.sub(r"(?i)<br\s*/?>", "\n", raw_html)         # <br>→\n
        body = body.replace("\r\n", "\n").replace("\r", "\n")   # 改行正規化
        body = re.sub(r"[\ud800-\udfff]", " ", body)            # 念のため本文にも
        safe = html.escape(body)

        color = "#000" if "◆" in dt_text else "#666"
        post_html = (
            f'<div class="res-block" id="res{idx}" style="color:{color};">'
            f"<strong>{html.escape(dt_text)}</strong><br>"
            f'<pre class="aa">{safe}</pre>'
            f"</div>"
        )
        posts.append(post_html)

    return "\n".join(posts)

def render_page(posts_html: str):
    """Streamlitへ安全に埋め込み"""
    # 最終ガード：UTF-8に一度通す（置換）
    safe_html = posts_html.encode("utf-8", "replace").decode("utf-8")

    font_face = ""
    if font_base64:
        font_face = f"""
        @font-face {{
          font-family: 'AAFont';
          src: url(data:font/woff2;base64,{font_base64}) format('woff2');
          font-weight: normal;
          font-style: normal;
          font-display: swap;
        }}
        """

    components.html(f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<style>
{font_face}
:root {{
  --aa-font: {'AAFont' if font_base64 else 'monospace'};
}}
html, body {{
  margin: 0;
  padding: 6px;
  font-family: var(--aa-font), monospace;
  background: #fdfdfd;
}}
.res-block {{
  background: transparent;
  border: none;
  padding: 0;
  margin: 0 0 .6em 0;
}}
pre.aa {{
  font-family: var(--aa-font), monospace;
  font-size: 14px;
  line-height: 1.4;
  white-space: pre;       /* 改行のみ尊重 */
  text-wrap: nowrap;      /* iOS 17+ */
  word-break: normal;
  overflow-wrap: normal;
  -webkit-hyphens: none;
  hyphens: none;
  overflow-x: auto;       /* 横スクロール */
  font-variant-ligatures: none;
  -webkit-text-size-adjust: 100%;
}}
strong {{ font-weight: bold; }}
</style>
</head>
<body>
{safe_html}
</body>
</html>""", height=3000, scrolling=True)

# --- action ---
if st.button("読み込む"):
    if url_value.strip() == "":
        st.warning("URLを入力してください。")
    else:
        try:
            u = normalize_url(url_value)
            hist = st.session_state["url_history"]
            if u in hist: hist.remove(u)
            hist.append(u)
            if len(hist) > 5: hist.pop(0)

            doc = fetch_html(u)
            posts_html = extract_posts(doc)
            render_page(posts_html)
        except requests.exceptions.MissingSchema:
            st.error("URLが正しくありません。http:// または https:// から始めてください。")
        except Exception as e:
            st.error(f"読み込み中にエラーが発生しました: {e}")
