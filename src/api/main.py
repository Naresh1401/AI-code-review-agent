"""
src/api/main.py — FastAPI webhook + manual review API
"""
import os, json, time
from typing import Dict, Optional, Any
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
from src.analyzer.code_reviewer import CodeReviewer, ReviewResult
from src.github.github_handler import GitHubHandler, verify_webhook_signature

app = FastAPI(title="AI Code Review Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_stats = {"reviews": 0, "comments_posted": 0, "total_ms": 0.0}


def get_reviewer():
    from src.analyzer.code_reviewer import CodeReviewer
    provider = os.getenv("LLM_PROVIDER", "openai")
    if provider == "anthropic":
        import anthropic
        class AnthrLLM:
            def __init__(self):
                self.client = anthropic.Anthropic()
                self.model  = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
            def generate(self, system, user):
                r = self.client.messages.create(model=self.model, max_tokens=2048,
                    system=system, messages=[{"role":"user","content":user}])
                return r.content[0].text
        llm = AnthrLLM()
    else:
        from openai import OpenAI
        class OAILLM:
            def __init__(self):
                self.client = OpenAI()
                self.model  = os.getenv("LLM_MODEL", "gpt-4o")
            def generate(self, system, user):
                r = self.client.chat.completions.create(
                    model=self.model, temperature=0.0, max_tokens=2048,
                    messages=[{"role":"system","content":system},{"role":"user","content":user}],
                    response_format={"type":"json_object"})
                return r.choices[0].message.content
        llm = OAILLM()
    return CodeReviewer(llm)


class ManualReviewRequest(BaseModel):
    pr_title:       str
    pr_description: str = ""
    file_diffs:     Dict[str, str]   # {filename: diff_text}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stats")
async def stats():
    return {**_stats, "avg_ms": _stats["total_ms"] / max(_stats["reviews"], 1)}


@app.post("/review")
async def manual_review(request: ManualReviewRequest):
    """Review a PR diff manually (no GitHub integration needed)."""
    reviewer = get_reviewer()
    result   = reviewer.review_pr(
        pr_title       = request.pr_title,
        pr_description = request.pr_description,
        file_diffs     = request.file_diffs,
    )
    _stats["reviews"]        += 1
    _stats["comments_posted"] += len(result.comments)
    _stats["total_ms"]        += result.latency_ms
    return result.to_dict()


@app.post("/webhook/github")
async def github_webhook(
    request:         Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event:      Optional[str] = Header(None),
):
    """
    GitHub webhook endpoint.
    Configure in GitHub: Settings → Webhooks → Add webhook
    Events: Pull requests
    """
    payload = await request.body()

    # Verify signature
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if secret and x_hub_signature_256:
        if not verify_webhook_signature(payload, x_hub_signature_256, secret):
            raise HTTPException(401, "Invalid webhook signature")

    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    data   = json.loads(payload)
    action = data.get("action")

    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "action": action}

    repo_name  = data["repository"]["full_name"]
    pr_number  = data["pull_request"]["number"]
    pr_title   = data["pull_request"]["title"]
    pr_body    = data["pull_request"].get("body", "")

    logger.info(f"PR #{pr_number} {action}: {pr_title}")
    background_tasks.add_task(
        _process_pr_webhook, repo_name, pr_number, pr_title, pr_body
    )
    return {"status": "processing", "pr": pr_number}


async def _process_pr_webhook(repo_name, pr_number, pr_title, pr_body):
    """Background task: review PR and post comments."""
    try:
        gh       = GitHubHandler()
        reviewer = get_reviewer()

        diffs  = gh.get_pr_diffs(repo_name, pr_number)
        result = reviewer.review_pr(pr_title, pr_body, diffs)

        gh.post_review(repo_name, pr_number, result)
        logger.info(f"Review posted for PR #{pr_number}: score={result.overall_score}")

        _stats["reviews"]        += 1
        _stats["comments_posted"] += len(result.comments)
        _stats["total_ms"]        += result.latency_ms
    except Exception as e:
        logger.error(f"PR review failed: {e}")
