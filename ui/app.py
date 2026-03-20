"""
ui/app.py — Streamlit UI for AI Code Review Agent
"""
import streamlit as st
import requests
import json
import plotly.graph_objects as go
import plotly.express as px

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Code Review", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.critical { color:#dc3545; font-weight:bold; }
.high     { color:#fd7e14; font-weight:bold; }
.medium   { color:#ffc107; font-weight:bold; }
.low      { color:#17a2b8; font-weight:bold; }
.info     { color:#6c757d; }
.comment-card {
    background:#f8f9fa; border-radius:6px;
    padding:12px 16px; margin:6px 0;
    border-left:4px solid #dee2e6;
}
.card-critical { border-left-color:#dc3545; }
.card-high     { border-left-color:#fd7e14; }
.card-medium   { border-left-color:#ffc107; }
.card-low      { border-left-color:#17a2b8; }
.score-badge {
    font-size:3em; font-weight:bold; text-align:center;
    padding:20px; border-radius:12px;
}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🔍 AI Code Review")
    st.caption("Automated PR review powered by LLM")
    st.divider()
    try:
        h = requests.get(f"{API_URL}/health", timeout=5).json()
        st.success("🟢 API Connected")
        s = requests.get(f"{API_URL}/stats", timeout=5).json()
        st.metric("Reviews Done",     s.get("reviews", 0))
        st.metric("Comments Posted",  s.get("comments_posted", 0))
        st.metric("Avg Review Time",  f"{s.get('avg_ms', 0):.0f}ms")
    except:
        st.error("🔴 API Offline — run: make run")
        st.stop()

tab_review, tab_examples = st.tabs(["📝 Review Code", "📚 Examples"])

# ── REVIEW TAB ────────────────────────────────────────────────────────────
with tab_review:
    st.header("Submit Code for Review")

    col1, col2 = st.columns([2, 1])
    with col1:
        pr_title = st.text_input("PR Title", placeholder="Add user authentication with JWT")
    with col2:
        filename = st.text_input("Filename", placeholder="auth.py")

    pr_desc = st.text_area("PR Description (optional)",
                           placeholder="Implements JWT-based authentication...", height=80)

    diff_input = st.text_area(
        "Code Diff (paste your git diff or just the new code)",
        height=300,
        placeholder="""+ def login(user, password):
+     query = f"SELECT * FROM users WHERE user={user}"
+     db.execute(query)
+
+ SECRET = "hardcoded_secret_123"
+
+ def get_all_users():
+     return db.execute("SELECT * FROM users")""",
    )

    if st.button("🔍 Review Code", type="primary", use_container_width=True):
        if not diff_input.strip():
            st.warning("Please paste some code to review.")
        else:
            fname = filename.strip() or "main.py"
            with st.spinner("Analyzing code..."):
                resp = requests.post(f"{API_URL}/review", json={
                    "pr_title":       pr_title or "Code Review",
                    "pr_description": pr_desc,
                    "file_diffs":     {fname: diff_input},
                }, timeout=120)

            if resp.ok:
                r = resp.json()

                # Score
                score = r.get("overall_score", 0)
                color = "#28a745" if score >= 80 else "#fd7e14" if score >= 60 else "#dc3545"
                verdict = "✅ APPROVED" if r.get("approved") else "❌ CHANGES REQUESTED"

                col_s, col_v, col_t = st.columns(3)
                with col_s:
                    st.markdown(
                        f'<div class="score-badge" style="color:{color};background:#f8f9fa">'
                        f'{score}/100</div>', unsafe_allow_html=True
                    )
                with col_v:
                    st.markdown(f"### Verdict\n{verdict}")
                with col_t:
                    counts = r.get("comment_counts", {})
                    st.markdown(f"""### Issues Found
🔴 Critical: **{counts.get('critical',0)}**  
🟠 High: **{counts.get('high',0)}**  
🟡 Medium: **{counts.get('medium',0)}**  
🔵 Low: **{counts.get('low',0)}**""")

                # Summary
                st.markdown("### Summary")
                st.info(r.get("summary","").replace("❌","").replace("✅","").replace("⚠️","").strip())

                # Comments
                comments = r.get("comments", [])
                if comments:
                    st.markdown(f"### Review Comments ({len(comments)})")

                    # Severity filter
                    severities   = list({c["severity"] for c in comments})
                    show_sevs    = st.multiselect("Filter by severity", severities, default=severities)
                    filtered     = [c for c in comments if c["severity"] in show_sevs]

                    for c in filtered:
                        sev   = c["severity"]
                        cat   = c["category"]
                        cls   = f"card-{sev}"
                        sev_cls = sev
                        icons = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🔵","info":"ℹ️"}
                        icon  = icons.get(sev, "💬")
                        st.markdown(
                            f'<div class="comment-card {cls}">'
                            f'<b>{icon} [{sev.upper()}] {cat.title()}</b> — '
                            f'<code>{c["file"]}:{c["line"]}</code><br>'
                            f'{c["message"]}'
                            + (f'<br><i>💡 {c["suggestion"]}</i>' if c.get("suggestion") else "")
                            + (f'<br><pre style="margin:4px 0 0 0;font-size:0.85em">{c["code_fix"]}</pre>' if c.get("code_fix") else "")
                            + '</div>',
                            unsafe_allow_html=True
                        )

                    # Chart
                    if len(comments) > 1:
                        cat_counts = {}
                        for c in comments:
                            cat_counts[c["category"]] = cat_counts.get(c["category"], 0) + 1
                        fig = px.bar(
                            x=list(cat_counts.keys()), y=list(cat_counts.values()),
                            labels={"x": "Category", "y": "Count"},
                            title="Issues by Category", height=250,
                            color=list(cat_counts.values()),
                            color_continuous_scale="RdYlGn_r",
                        )
                        fig.update_coloraxes(showscale=False)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("🎉 No issues found — code looks great!")

                with st.expander("📋 Raw JSON"):
                    st.json(r)
            else:
                st.error(f"Review failed: {resp.text}")

# ── EXAMPLES TAB ─────────────────────────────────────────────────────────
with tab_examples:
    st.header("Example Code to Review")
    st.info("Copy any example into the Review tab to see it in action.")

    examples = {
        "🔴 SQL Injection": {
            "filename": "database.py",
            "diff": """+def get_user(user_id):
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    return db.execute(query)
+
+def search_products(name):
+    sql = "SELECT * FROM products WHERE name = '" + name + "'"
+    return db.fetchall(sql)"""
        },
        "🔴 Hardcoded Secrets": {
            "filename": "config.py",
            "diff": """+SECRET_KEY = "my_super_secret_key_123"
+DATABASE_PASSWORD = "admin123"
+AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
+API_TOKEN = "ghp_16C7e42F292c6912E7710c838347Ae298G5"
+
+def get_config():
+    return {"secret": SECRET_KEY, "db_pass": DATABASE_PASSWORD}"""
        },
        "🟠 Off-by-one Bug": {
            "filename": "utils.py",
            "diff": """+def process_items(items):
+    results = []
+    for i in range(len(items) + 1):  # Bug: should be len(items)
+        results.append(items[i].process())
+    return results
+
+def get_last(lst):
+    return lst[len(lst)]  # Bug: index out of range, should be len(lst)-1"""
        },
        "✅ Clean Code": {
            "filename": "auth.py",
            "diff": """+import os
+import hashlib
+from typing import Optional
+
+def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
+    \"\"\"Hash a password with a random salt. Returns (hashed, salt).\"\"\"
+    if salt is None:
+        salt = os.urandom(32).hex()
+    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
+    return hashed.hex(), salt"""
        },
    }

    for title, ex in examples.items():
        with st.expander(title):
            st.code(ex["diff"], language="diff")
            st.caption(f"File: `{ex['filename']}`")
