@@
-import html
+import html
 import streamlit.components.v1 as components
 import base64
 import os
 import re
+from bs4 import UnicodeDammit
@@
 url = st.text_input("AAページのURLを入力してください（http:// または https://）", key="url")
@@
-            headers = {"User-Agent": "Mozilla/5.0"}
-            response = requests.get(normalized_url, headers=headers, timeout=10)
-            decoded = response.content.decode("shift_jis", errors="ignore")
-            soup = BeautifulSoup(decoded, "html.parser")
+            headers = {"User-Agent": "Mozilla/5.0"}
+            response = requests.get(normalized_url, headers=headers, timeout=10)
+            # 1) 文字コードを自動判定しつつ安全にデコード（サロゲート混入を防ぐ）
+            dm = UnicodeDammit(response.content)
+            decoded = dm.unicode_markup or response.content.decode(response.apparent_encoding or "utf-8", errors="replace")
+            # 念のため：U+D800–DFFF を除去（以降のUTF-8再エンコードで落ちないように）
+            decoded = re.sub(r"[\ud800-\udfff]", " ", decoded)
+            soup = BeautifulSoup(decoded, "html.parser")
@@
-            posts = []
+            posts = []
             for index, (dt, dd) in enumerate(zip(dt_blocks, dd_blocks), start=1):
-                dt_text = dt.get_text(strip=True)
-                dd_raw = dd.get_text("\n")
-                dd_escaped = html.escape(dd_raw)
+                # 2) ヘッダと本文にサロゲートがあれば除去
+                dt_text = re.sub(r"[\ud800-\udfff]", " ", dt.get_text(strip=True))
+                # 3) 本文は innerHTML を保持して <br> をだけ \n に変換（改行を増やさない）
+                raw_html = dd.decode_contents()  # get_text("\n") は使わない
+                body = re.sub(r"(?i)<br\s*/?>", "\n", raw_html)
+                body = body.replace("\r\n", "\n").replace("\r", "\n")
+                body = re.sub(r"[\ud800-\udfff]", " ", body)
+                dd_escaped = html.escape(body)
                 color = "#000" if "◆" in dt_text else "#666"
                 post_html = f'<div class="res-block" id="res{index}" style="color:{color};"><strong>{dt_text}</strong><br><pre>{dd_escaped}</pre></div>'
                 posts.append(post_html)
 
-            all_posts_html = "\n".join(posts)
+            all_posts_html = "\n".join(posts)
+            # 4) 最終埋め込み直前にUTF-8へ一度通して安全化
+            safe_posts_html = all_posts_html.encode("utf-8", "replace").decode("utf-8")
@@
-            components.html(f"""
+            components.html(f"""
             <html>
             <head>
-            <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=10, user-scalable=yes">
+            <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=10, user-scalable=yes">
             <style>
             @font-face {
                 font-family: 'AAFont';
                 src: url(data:font/woff2;base64,{font_base64}) format('woff2');
                 font-weight: normal;
                 font-style: normal;
                 font-display: swap;
             }
             body {
                 margin: 0;
                 padding: 5px;
                 font-family: 'AAFont';
             }
             pre {
                 font-family: 'AAFont';
                 font-size: 15px;
                 line-height: 1.15;
-                white-space: pre;
+                white-space: pre;        /* 改行だけ尊重。折返しはしない */
+                text-wrap: nowrap;       /* iOS 17+ の新挙動で折返しされるのを防止 */
+                word-break: normal;
+                overflow-wrap: normal;
+                -webkit-text-size-adjust: 100%;
                 overflow-x: auto;
             }
             .res-block {
                 background-color: transparent;
                 border: none;
                 padding: 0;
                 margin-bottom: 1.2em;
             }
             </style>
             </head>
             <body>
-            {all_posts_html}
+            {safe_posts_html}
             </body>
             </html>
             """, height=3000, scrolling=True)
