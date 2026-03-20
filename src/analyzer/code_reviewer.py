"""
src/analyzer/code_reviewer.py
===============================
LLM-powered code review engine.

Reviews code diffs for:
  - Bugs and logic errors
  - Security vulnerabilities (injection, secrets, auth issues)
  - Performance problems
  - Code style and maintainability
  - Missing test coverage
  - Documentation gaps

Produces structured, line-level comments ready to post as GitHub PR review comments.
"""

import re
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class Severity(str, Enum):
    CRITICAL  = "critical"   # Security issue, data loss risk — must fix
    HIGH      = "high"       # Bug, major performance issue — should fix
    MEDIUM    = "medium"     # Code smell, maintainability — consider fixing
    LOW       = "low"        # Minor style, optional improvement
    INFO      = "info"       # Informational, no action needed


class Category(str, Enum):
    BUG           = "bug"
    SECURITY      = "security"
    PERFORMANCE   = "performance"
    STYLE         = "style"
    TESTING       = "testing"
    DOCUMENTATION = "documentation"
    LOGIC         = "logic"


@dataclass
class ReviewComment:
    """A single review comment on a specific line."""
    file:       str
    line:       int
    severity:   Severity
    category:   Category
    message:    str
    suggestion: Optional[str] = None    # Suggested fix
    code_fix:   Optional[str] = None    # Suggested replacement code

    def to_dict(self) -> Dict:
        return {
            "file":       self.file,
            "line":       self.line,
            "severity":   self.severity.value,
            "category":   self.category.value,
            "message":    self.message,
            "suggestion": self.suggestion,
            "code_fix":   self.code_fix,
        }


@dataclass
class ReviewResult:
    """Full review result for a PR or file."""
    pr_title:        str
    files_reviewed:  int
    total_lines:     int
    comments:        List[ReviewComment] = field(default_factory=list)
    summary:         str = ""
    overall_score:   int = 0    # 0–100
    approved:        bool = False
    latency_ms:      float = 0.0

    @property
    def by_severity(self) -> Dict[str, List[ReviewComment]]:
        result = {s.value: [] for s in Severity}
        for c in self.comments:
            result[c.severity.value].append(c)
        return result

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.comments if c.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for c in self.comments if c.severity == Severity.HIGH)

    def to_dict(self) -> Dict:
        return {
            "pr_title":       self.pr_title,
            "files_reviewed": self.files_reviewed,
            "total_lines":    self.total_lines,
            "overall_score":  self.overall_score,
            "approved":       self.approved,
            "summary":        self.summary,
            "latency_ms":     round(self.latency_ms, 1),
            "comment_counts": {
                "critical": self.critical_count,
                "high":     self.high_count,
                "medium":   sum(1 for c in self.comments if c.severity == Severity.MEDIUM),
                "low":      sum(1 for c in self.comments if c.severity == Severity.LOW),
                "total":    len(self.comments),
            },
            "comments": [c.to_dict() for c in self.comments],
        }


# ── Prompts ──────────────────────────────────────────────────────────────

REVIEW_SYSTEM_PROMPT = """You are an expert senior software engineer performing a thorough code review.

Your job is to identify:
1. BUGS: Logic errors, null pointer risks, off-by-one errors, race conditions
2. SECURITY: SQL injection, XSS, hardcoded secrets/passwords/tokens, insecure auth, path traversal
3. PERFORMANCE: N+1 queries, missing indexes, blocking I/O in async, unnecessary loops
4. STYLE: Naming, readability, complexity, dead code, magic numbers
5. TESTING: Missing edge case tests, untested error paths
6. DOCUMENTATION: Missing docstrings for public APIs, unclear variable names

For each issue found, provide a JSON comment object:
{
  "file": "filename.py",
  "line": <line number>,
  "severity": "critical|high|medium|low|info",
  "category": "bug|security|performance|style|testing|documentation|logic",
  "message": "Clear description of the problem",
  "suggestion": "How to fix it (one sentence)",
  "code_fix": "Concrete code snippet showing the fix (optional)"
}

Return a JSON object:
{
  "comments": [...],
  "summary": "Overall assessment in 2-3 sentences",
  "overall_score": <0-100>,
  "approved": <true if no critical/high issues>
}

Be specific, actionable, and constructive. Cite line numbers accurately."""


def build_review_prompt(diff: str, filename: str, pr_description: str = "") -> str:
    return f"""Review this code change.

File: {filename}
PR Description: {pr_description or 'Not provided'}

Code diff (+ = added, - = removed):
```
{diff[:6000]}
```

Focus especially on security vulnerabilities and bugs.
Return ONLY valid JSON."""


# ── Reviewer ─────────────────────────────────────────────────────────────

class CodeReviewer:
    """
    LLM-based code reviewer.

    Reviews individual file diffs and aggregates results across a full PR.
    """

    # File types to skip (binary, generated, etc.)
    SKIP_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
        '.pdf', '.zip', '.tar', '.whl', '.pyc',
        '.lock', '.sum', 'package-lock.json',
    }

    def __init__(self, llm):
        self.llm = llm

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    def review_file(
        self,
        filename: str,
        diff: str,
        pr_description: str = "",
    ) -> List[ReviewComment]:
        """Review a single file diff and return comments."""
        ext = '.' + filename.split('.')[-1] if '.' in filename else ''
        if ext.lower() in self.SKIP_EXTENSIONS:
            logger.debug(f"Skipping binary/generated file: {filename}")
            return []

        if len(diff.strip()) < 10:
            return []

        prompt = build_review_prompt(diff, filename, pr_description)

        try:
            raw = self.llm.generate(REVIEW_SYSTEM_PROMPT, prompt)
            data = self._parse_response(raw)
            comments = []
            for c in data.get("comments", []):
                try:
                    comments.append(ReviewComment(
                        file       = filename,
                        line       = int(c.get("line", 1)),
                        severity   = Severity(c.get("severity", "low")),
                        category   = Category(c.get("category", "style")),
                        message    = c.get("message", ""),
                        suggestion = c.get("suggestion"),
                        code_fix   = c.get("code_fix"),
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping malformed comment: {e}")
            return comments
        except Exception as e:
            logger.error(f"Review failed for {filename}: {e}")
            return []

    def review_pr(
        self,
        pr_title:       str,
        pr_description: str,
        file_diffs:     Dict[str, str],  # {filename: diff_text}
    ) -> ReviewResult:
        """
        Review a full pull request.

        Args:
            pr_title:       PR title
            pr_description: PR description / body
            file_diffs:     Dict mapping filename → diff text
        """
        import time
        t0 = time.perf_counter()

        all_comments: List[ReviewComment] = []
        total_lines = 0

        for filename, diff in file_diffs.items():
            logger.info(f"  Reviewing: {filename}")
            comments = self.review_file(filename, diff, pr_description)
            all_comments.extend(comments)
            total_lines += diff.count('\n')

        # Generate overall summary
        summary, score, approved = self._generate_summary(
            pr_title, all_comments, total_lines
        )

        return ReviewResult(
            pr_title       = pr_title,
            files_reviewed = len(file_diffs),
            total_lines    = total_lines,
            comments       = all_comments,
            summary        = summary,
            overall_score  = score,
            approved       = approved,
            latency_ms     = (time.perf_counter() - t0) * 1000,
        )

    def _generate_summary(
        self,
        pr_title: str,
        comments: List[ReviewComment],
        total_lines: int,
    ) -> tuple[str, int, bool]:
        """Generate a human-readable summary of the review."""
        critical = sum(1 for c in comments if c.severity == Severity.CRITICAL)
        high     = sum(1 for c in comments if c.severity == Severity.HIGH)
        medium   = sum(1 for c in comments if c.severity == Severity.MEDIUM)

        if critical > 0:
            status  = f"❌ CHANGES REQUESTED — {critical} critical issue(s) must be fixed before merging."
            score   = max(0, 40 - critical * 15)
            approved = False
        elif high > 0:
            status  = f"⚠️ CHANGES REQUESTED — {high} high-severity issue(s) should be addressed."
            score   = max(40, 70 - high * 10)
            approved = False
        elif medium > 2:
            status  = f"💬 APPROVED WITH COMMENTS — {medium} medium-severity suggestions."
            score   = max(70, 90 - medium * 3)
            approved = True
        else:
            status  = "✅ APPROVED — Code looks good."
            score   = 95
            approved = True

        summary = (
            f"{status}\n"
            f"Reviewed {total_lines} lines across {len(set(c.file for c in comments))} files. "
            f"Found {len(comments)} issues: {critical} critical, {high} high, {medium} medium."
        )
        return summary, score, approved

    def _parse_response(self, response: str) -> Dict:
        clean = re.sub(r"```(?:json)?|```", "", response).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {"comments": [], "summary": "Parse error", "overall_score": 50, "approved": False}
