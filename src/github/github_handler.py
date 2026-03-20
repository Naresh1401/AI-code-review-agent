"""
src/github/github_handler.py
==============================
GitHub PR integration — fetches diffs and posts review comments.

Handles:
  - Fetching PR file diffs via GitHub API
  - Posting inline review comments on specific lines
  - Posting review summary as PR review (approve / request changes)
  - Webhook payload parsing
"""

import os
import hmac
import hashlib
from typing import Dict, List, Optional
from loguru import logger

from src.analyzer.code_reviewer import ReviewResult, ReviewComment, Severity


class GitHubHandler:
    """
    Wraps PyGithub to interact with GitHub PRs.
    """

    def __init__(self, token: Optional[str] = None):
        try:
            from github import Github
            self.gh    = Github(token or os.environ["GITHUB_TOKEN"])
            self.token = token or os.environ.get("GITHUB_TOKEN", "")
        except ImportError:
            raise ImportError("Install PyGithub: pip install PyGithub")

    def get_pr_diffs(self, repo_name: str, pr_number: int) -> Dict[str, str]:
        """
        Fetch all file diffs for a PR.

        Returns:
            Dict[filename → unified_diff_text]
        """
        repo = self.gh.get_repo(repo_name)
        pr   = repo.get_pull(pr_number)

        diffs = {}
        for file in pr.get_files():
            if file.patch:  # patch is None for binary files
                diffs[file.filename] = file.patch
        logger.info(f"Fetched diffs for {len(diffs)} files from PR #{pr_number}")
        return diffs

    def get_pr_metadata(self, repo_name: str, pr_number: int) -> Dict:
        """Get PR title, description, and base branch."""
        repo = self.gh.get_repo(repo_name)
        pr   = repo.get_pull(pr_number)
        return {
            "title":       pr.title,
            "body":        pr.body or "",
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "author":      pr.user.login,
            "changed_files": pr.changed_files,
        }

    def post_review(
        self,
        repo_name:  str,
        pr_number:  int,
        result:     ReviewResult,
    ) -> bool:
        """
        Post the full review to GitHub as a PR review.

        Posts:
          - Individual inline comments on each flagged line
          - Overall review with approve/request changes verdict
        """
        repo = self.gh.get_repo(repo_name)
        pr   = repo.get_pull(pr_number)

        # Determine review event
        if result.approved:
            event = "APPROVE"
        elif result.critical_count > 0 or result.high_count > 0:
            event = "REQUEST_CHANGES"
        else:
            event = "COMMENT"

        # Build inline comment list
        # GitHub requires comments to be on valid diff positions
        inline_comments = []
        for comment in result.comments:
            inline_comments.append({
                "path":     comment.file,
                "line":     comment.line,
                "body":     self._format_comment(comment),
            })

        try:
            pr.create_review(
                body     = result.summary,
                event    = event,
                comments = inline_comments[:50],  # GitHub limit: 50 inline comments per review
            )
            logger.info(f"Posted review to PR #{pr_number}: {event}")
            return True
        except Exception as e:
            logger.error(f"Failed to post review: {e}")
            # Fallback: post as a regular comment
            try:
                pr.create_issue_comment(
                    f"## 🤖 AI Code Review\n\n{result.summary}\n\n"
                    + self._format_comments_as_markdown(result.comments)
                )
                return True
            except Exception as e2:
                logger.error(f"Fallback comment also failed: {e2}")
                return False

    def _format_comment(self, comment: ReviewComment) -> str:
        """Format a ReviewComment as a GitHub markdown comment."""
        icons = {
            "critical": "🔴",
            "high":     "🟠",
            "medium":   "🟡",
            "low":      "🔵",
            "info":     "ℹ️",
        }
        icon = icons.get(comment.severity.value, "💬")
        parts = [
            f"{icon} **[{comment.severity.value.upper()}] {comment.category.value.title()}**",
            f"\n{comment.message}",
        ]
        if comment.suggestion:
            parts.append(f"\n💡 **Suggestion:** {comment.suggestion}")
        if comment.code_fix:
            parts.append(f"\n```python\n{comment.code_fix}\n```")
        return "\n".join(parts)

    def _format_comments_as_markdown(self, comments: List[ReviewComment]) -> str:
        if not comments:
            return "_No specific issues found._"
        lines = []
        for c in comments[:20]:
            lines.append(
                f"- **{c.file}:{c.line}** [{c.severity.value}] {c.category.value}: {c.message}"
            )
        if len(comments) > 20:
            lines.append(f"\n_... and {len(comments)-20} more issues._")
        return "\n".join(lines)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook HMAC-SHA256 signature.

    GitHub sends X-Hub-Signature-256: sha256=<hex_digest>
    We verify the payload against our webhook secret.
    """
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
