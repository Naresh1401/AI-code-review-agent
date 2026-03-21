"""
ui/app.py — Streamlit UI for AI Code Review Agent
Premium glassmorphism design
"""
import streamlit as st
import requests
import json
import plotly.graph_objects as go
import plotly.express as px

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Code Review Agent", page_icon="🔍", layout="wide")

# ── Premium CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

.stApp {
    background: linear-gradient(135deg, #0c1222 0%, #1a1f35 40%, #0d1b2a 100%);
}
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; }
header[data-testid="stHeader"] { background: transparent; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c1222 0%, #0a0f1e 100%) !important;
    border-right: 1px solid rgba(16,185,129,0.1);
}
section[data-testid="stSidebar"] .stMarkdown { color: #d1d5db; }

.hero {
    text-align: center; padding: 40px 20px 20px 20px;
}
.hero h1 {
    font-size: 3rem; font-weight: 800;
    background: linear-gradient(135deg, #10b981, #06b6d4, #8b5cf6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 8px; letter-spacing: -1px;
}
.hero p { color: #9ca3af; font-size: 1.15rem; font-weight: 300; }

.glass {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(16,185,129,0.1);
    border-radius: 16px; padding: 24px; margin: 12px 0; color: #d1d5db;
}

.score-badge {
    font-size: 3.5em; font-weight: 800; text-align: center;
    padding: 24px; border-radius: 16px;
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
}

.metric-glass {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(16,185,129,0.1);
    border-radius: 14px; padding: 20px; text-align: center;
}
.metric-glass .value {
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(135deg, #10b981, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-glass .label { color: #9ca3af; font-size: 0.85rem; margin-top: 4px; }

.comment-card {
    background: rgba(255,255,255,0.03);
    border-radius: 10px; padding: 16px 20px; margin: 8px 0;
    border-left: 4px solid rgba(107,114,128,0.4);
    color: #d1d5db; transition: transform 0.2s ease;
    font-size: 0.95em;
}
.comment-card:hover { transform: translateX(4px); }
.card-critical { border-left-color: #ef4444; background: rgba(239,68,68,0.04); }
.card-high     { border-left-color: #f59e0b; background: rgba(245,158,11,0.04); }
.card-medium   { border-left-color: #eab308; background: rgba(234,179,8,0.04); }
.card-low      { border-left-color: #06b6d4; background: rgba(6,182,212,0.04); }

.summary-box {
    background: rgba(16,185,129,0.06);
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 12px; padding: 18px; color: #d1d5db;
    line-height: 1.7;
}

.verdict-approved {
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05));
    border: 1px solid rgba(16,185,129,0.4);
    border-radius: 14px; padding: 20px; text-align: center;
    color: #34d399; font-size: 1.5rem; font-weight: 700;
}
.verdict-changes {
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05));
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: 14px; padding: 20px; text-align: center;
    color: #fca5a5; font-size: 1.5rem; font-weight: 700;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.02); border-radius: 12px; padding: 4px; gap: 4px;
}
.stTabs [data-baseweb="tab"] { border-radius: 8px; color: #9ca3af; font-weight: 500; }
.stTabs [aria-selected="true"] {
    background: rgba(16,185,129,0.15) !important; color: #6ee7b7 !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #10b981, #06b6d4) !important;
    border: none !important; border-radius: 10px !important;
    color: #0c1222 !important; font-weight: 700 !important;
    transition: all 0.3s ease !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(16,185,129,0.3) !important;
}

.stTextArea textarea, .stTextInput input {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(16,185,129,0.12) !important;
    border-radius: 10px !important; color: #d1d5db !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.streamlit-expanderHeader {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 8px !important; color: #9ca3af !important;
}
.js-plotly-plot .plotly .main-svg { background: transparent !important; }

/* Streamlit overrides */
footer, #MainMenu, .stDeployButton, div[data-testid="stDecoration"] { display: none !important; }
[data-testid="stAppViewContainer"] { background: transparent !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebarContent"] { background: transparent !important; }
[data-testid="stBottomBlockContainer"] { background: transparent !important; }
div[data-testid="stMetricValue"] > div { color: #e2e8f0 !important; }
div[data-testid="stMetricDelta"] { color: #9ca3af !important; }
div[data-testid="stMetricLabel"] { color: #9ca3af !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🔍 AI Code Review Agent</h1>
    <p>Automated PR analysis — security vulnerabilities, bugs, best practices, with fix suggestions</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Review Stats")
    st.caption("Automated code quality insights")
    st.divider()
    try:
        h = requests.get(f"{API_URL}/health", timeout=5).json()
        st.success("🟢 API Connected")
        s = requests.get(f"{API_URL}/stats", timeout=5).json()
        st.metric("Reviews Done",    s.get("reviews", 0))
        st.metric("Comments Posted", s.get("comments_posted", 0))
        st.metric("Avg Review Time", f"{s.get('avg_ms', 0):.0f}ms")
    except Exception:
        st.error("🔴 API Offline — run: make run")
        st.stop()
    st.divider()
    st.caption("Built with OpenAI · FastAPI · Streamlit")

    st.divider()
    st.markdown("""
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;margin-top:8px;">
        <div style="font-weight:700;font-size:1rem;color:#e2e8f0;margin-bottom:6px;">👨‍💻 Naresh</div>
        <div style="font-size:0.8rem;color:#9ca3af;line-height:1.6;">
            GenAI Engineer · Full-Stack ML<br>
            <b style="color:#10b981;">Skills:</b> LLMs · RAG · Fine-tuning · LangChain · FastAPI · Docker<br>
            <b style="color:#10b981;">Stack:</b> Python · OpenAI · FAISS · Qdrant · Streamlit
        </div>
        <div style="margin-top:10px;font-size:0.75rem;">
            <a href="https://github.com/Naresh1401" style="color:#10b981;text-decoration:none;">GitHub</a>
        </div>
        <details style="margin-top:10px;">
            <summary style="color:#9ca3af;font-size:0.8rem;cursor:pointer;">🚀 More Projects</summary>
            <div style="font-size:0.75rem;color:#9ca3af;margin-top:8px;line-height:1.8;">
                <a href="https://llm-safety-guardrails.onrender.com" style="color:#7c3aed;text-decoration:none;">LLM Safety Guardrails</a><br>
                <a href="https://text-to-sql-agent-2za9.onrender.com" style="color:#64ffda;text-decoration:none;">Text-to-SQL Agent</a><br>
                <a href="https://intelligent-document-processing-qyo8.onrender.com" style="color:#a855f7;text-decoration:none;">Intelligent Doc Processing</a><br>
                <a href="https://meeting-intelligent-platform.onrender.com" style="color:#38bdf8;text-decoration:none;">Meeting Intelligence</a><br>
                <a href="https://enterprise-rag-pipeline.onrender.com" style="color:#818cf8;text-decoration:none;">Enterprise RAG Pipeline</a><br>
                <a href="https://financial-llm-assistant.onrender.com" style="color:#f59e0b;text-decoration:none;">Financial LLM Assistant</a>
            </div>
        </details>
    </div>
    """, unsafe_allow_html=True)

tab_review, tab_examples = st.tabs(["📝 Review Code", "📚 Example Vulnerabilities"])

# ── REVIEW TAB ────────────────────────────────────────────────────────────
with tab_review:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("#### Submit Code for Review")

    col1, col2 = st.columns([2, 1])
    with col1:
        pr_title = st.text_input("PR Title", placeholder="Add user authentication with JWT")
    with col2:
        filename = st.text_input("Filename", placeholder="auth.py")

    pr_desc = st.text_area("PR Description (optional)",
                           placeholder="Implements JWT-based authentication...", height=80)

    diff_input = st.text_area(
        "Code Diff (paste your git diff or just the new code)",
        height=280,
        placeholder="""+ def login(user, password):
+     query = f"SELECT * FROM users WHERE user={user}"
+     db.execute(query)
+
+ SECRET = "hardcoded_secret_123"
+
+ def get_all_users():
+     return db.execute("SELECT * FROM users")""",
    )
    st.markdown('</div>', unsafe_allow_html=True)

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

                score = r.get("overall_score", 0)
                color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"

                col_s, col_v, col_t = st.columns(3)
                with col_s:
                    st.markdown(
                        f'<div class="score-badge" style="color:{color}">'
                        f'{score}/100</div>',
                        unsafe_allow_html=True
                    )
                with col_v:
                    if r.get("approved"):
                        st.markdown('<div class="verdict-approved">✅ APPROVED</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="verdict-changes">❌ CHANGES REQUESTED</div>',
                                    unsafe_allow_html=True)
                with col_t:
                    counts = r.get("comment_counts", {})
                    st.markdown(
                        f'<div class="metric-glass">'
                        f'<div style="text-align:left;color:#d1d5db;font-size:0.95rem">'
                        f'🔴 Critical: <b>{counts.get("critical", 0)}</b><br>'
                        f'🟠 High: <b>{counts.get("high", 0)}</b><br>'
                        f'🟡 Medium: <b>{counts.get("medium", 0)}</b><br>'
                        f'🔵 Low: <b>{counts.get("low", 0)}</b>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )

                st.markdown("#### Summary")
                summary_text = r.get("summary", "").replace("❌", "").replace("✅", "").replace("⚠️", "").strip()
                st.markdown(f'<div class="summary-box">{summary_text}</div>', unsafe_allow_html=True)

                comments = r.get("comments", [])
                if comments:
                    st.markdown(f"#### Review Comments ({len(comments)})")

                    severities = list({c["severity"] for c in comments})
                    show_sevs = st.multiselect("Filter by severity", severities, default=severities)
                    filtered = [c for c in comments if c["severity"] in show_sevs]

                    for c in filtered:
                        sev = c["severity"]
                        cat = c["category"]
                        cls = f"card-{sev}"
                        icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}
                        icon = icons.get(sev, "💬")
                        suggestion_html = f'<br><i style="color:#6ee7b7">💡 {c["suggestion"]}</i>' if c.get("suggestion") else ""
                        code_fix_html = f'<br><pre style="margin:6px 0 0 0;font-size:0.85em;color:#10b981;background:rgba(16,185,129,0.06);padding:8px;border-radius:6px">{c["code_fix"]}</pre>' if c.get("code_fix") else ""
                        st.markdown(
                            f'<div class="comment-card {cls}">'
                            f'<b>{icon} [{sev.upper()}] {cat.title()}</b> — '
                            f'<code style="color:#06b6d4">{c["file"]}:{c["line"]}</code><br>'
                            f'{c["message"]}'
                            f'{suggestion_html}{code_fix_html}'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                    if len(comments) > 1:
                        cat_counts = {}
                        for c in comments:
                            cat_counts[c["category"]] = cat_counts.get(c["category"], 0) + 1
                        fig = px.bar(
                            x=list(cat_counts.keys()), y=list(cat_counts.values()),
                            labels={"x": "Category", "y": "Count"},
                            title="Issues by Category", height=280,
                            color=list(cat_counts.values()),
                            color_continuous_scale="Tealgrn_r",
                        )
                        fig.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#9ca3af"),
                            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
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
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("#### 📚 Example Vulnerable Code")
    st.caption("Copy any example into the Review tab to see it analyzed")
    st.markdown('</div>', unsafe_allow_html=True)

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
