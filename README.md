# AI Code Review Agent

Automatically reviews GitHub Pull Requests for bugs, security vulnerabilities, performance issues, and style problems — posting inline comments directly on the PR.

## The Problem

Senior engineers spend 30–40% of their time on code reviews. Junior devs get inconsistent feedback. Security issues slip through. This agent provides instant, consistent, thorough reviews on every PR — freeing senior engineers to focus on architecture.

## Architecture

```
GitHub PR Opened/Updated
         │
         ▼ (webhook)
  ┌──────────────────┐
  │  FastAPI Server  │
  │  Webhook Handler │
  │  Sig Verification│
  └────────┬─────────┘
           │ (background task)
           ▼
  ┌──────────────────┐
  │  GitHub Handler  │  Fetch PR diffs via API
  │  get_pr_diffs()  │
  └────────┬─────────┘
           │
           ▼ (per file)
  ┌──────────────────┐
  │  Code Reviewer   │  Schema-driven LLM review
  │  review_file()   │  Bug / Security / Perf / Style
  │                  │  Per-line severity scores
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  ReviewResult    │  Aggregate all comments
  │  Score: 0-100    │  Approve / Request Changes
  │  Verdict         │
  └────────┬─────────┘
           │
           ▼
  GitHub PR Review Comments (inline)
  + Summary comment with overall score
```

## Quickstart

```bash
git clone https://github.com/Naresh1401/ai-code-review-agent
cd ai-code-review-agent
pip install -r requirements.txt
cp .env.example .env   # Add OPENAI_API_KEY + GITHUB_TOKEN
make run-api
```

### Manual Review (no GitHub needed)
```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_title": "Add user authentication",
    "pr_description": "Implements JWT auth",
    "file_diffs": {
      "auth.py": "+def login(user, password):\n+    query = f\"SELECT * FROM users WHERE user={user}\"\n+    SECRET = \"hardcoded123\""
    }
  }'
```

```json
{
  "overall_score": 15,
  "approved": false,
  "summary": "❌ CHANGES REQUESTED — 2 critical issues must be fixed.",
  "comment_counts": {"critical": 2, "high": 0, "total": 2},
  "comments": [
    {
      "file": "auth.py", "line": 2,
      "severity": "critical", "category": "security",
      "message": "SQL injection vulnerability — user input is directly interpolated",
      "suggestion": "Use parameterised queries: db.execute('SELECT * FROM users WHERE user=?', (user,))"
    },
    {
      "file": "auth.py", "line": 3,
      "severity": "critical", "category": "security",
      "message": "Hardcoded secret — never store secrets in source code",
      "suggestion": "Load from environment: SECRET = os.environ['SECRET_KEY']"
    }
  ]
}
```

### GitHub Webhook Setup
1. In your repo: Settings → Webhooks → Add webhook
2. Payload URL: `https://your-server.com/webhook/github`
3. Content type: `application/json`
4. Secret: your `GITHUB_WEBHOOK_SECRET`
5. Events: Pull requests

## What Gets Reviewed

| Category | Examples |
|---|---|
| 🔴 **Security** | SQL injection, XSS, hardcoded secrets, path traversal, insecure auth |
| 🟠 **Bugs** | Null pointer risks, off-by-one, race conditions, unhandled exceptions |
| 🟡 **Performance** | N+1 queries, blocking I/O in async, unnecessary loops |
| 🔵 **Style** | Naming, complexity, dead code, magic numbers |
| ℹ️ **Testing** | Missing edge cases, untested error paths |

## Running Tests

```bash
python tests/test_reviewer.py
```

## Project Structure

```
ai-code-review-agent/
├── src/
│   ├── analyzer/
│   │   └── code_reviewer.py    # LLM review engine
│   ├── github/
│   │   └── github_handler.py   # GitHub API + webhook
│   └── api/
│       └── main.py             # FastAPI webhook + manual review
├── tests/
│   └── test_reviewer.py        # 6 unit tests
└── requirements.txt
```

## Resume Talking Points

- Built AI code review agent that reviews GitHub PRs automatically via webhook, posting inline comments on flagged lines
- Implemented structured review schema detecting 7 issue categories (bugs, security, performance, style, testing, logic, documentation) with severity levels
- Security detection catches SQL injection, hardcoded secrets, insecure auth, and path traversal vulnerabilities
- Agent posts GitHub-native PR reviews (approve / request changes) with inline comments — integrates into existing developer workflows with zero friction
