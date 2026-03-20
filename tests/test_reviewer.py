"""tests/test_reviewer.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.analyzer.code_reviewer import (
    CodeReviewer, ReviewComment, ReviewResult, Severity, Category
)

SAMPLE_DIFF_SECURITY = """\
+def get_user(user_id):
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    return db.execute(query)
+
+PASSWORD = "admin123"
+SECRET_KEY = "hardcoded_secret_do_not_share"
"""

SAMPLE_DIFF_BUG = """\
+def divide(a, b):
+    return a / b
+
+def process_list(items):
+    for i in range(len(items) + 1):
+        print(items[i])
"""

SAMPLE_DIFF_CLEAN = """\
+def add(a: int, b: int) -> int:
+    \"\"\"Add two integers and return the result.\"\"\"
+    return a + b
"""

class MockLLM:
    """Returns canned review responses for testing."""
    def __init__(self, response_data):
        self.response_data = response_data
    def generate(self, system, user):
        import json
        return json.dumps(self.response_data)

def test_review_returns_comments():
    llm = MockLLM({
        "comments": [
            {"file": "app.py", "line": 2, "severity": "critical",
             "category": "security", "message": "SQL injection vulnerability",
             "suggestion": "Use parameterised queries", "code_fix": "db.execute('SELECT * FROM users WHERE id = ?', (user_id,))"}
        ],
        "summary": "Critical SQL injection found.", "overall_score": 20, "approved": False
    })
    reviewer = CodeReviewer(llm)
    result   = reviewer.review_pr("test PR", "", {"app.py": SAMPLE_DIFF_SECURITY})
    assert len(result.comments) == 1
    assert result.comments[0].severity == Severity.CRITICAL
    assert result.comments[0].category == Category.SECURITY
    assert result.approved == False
    print("✅ review returns structured comments")

def test_review_approved_clean_code():
    llm = MockLLM({"comments": [], "summary": "Looks good.", "overall_score": 95, "approved": True})
    reviewer = CodeReviewer(llm)
    result   = reviewer.review_pr("clean PR", "", {"utils.py": SAMPLE_DIFF_CLEAN})
    assert result.approved == True
    assert result.overall_score >= 90
    assert len(result.comments) == 0
    print("✅ clean code gets approved")

def test_skip_binary_files():
    llm      = MockLLM({"comments": [], "summary": "", "overall_score": 100, "approved": True})
    reviewer = CodeReviewer(llm)
    comments = reviewer.review_file("image.png", "binary diff", "")
    assert comments == []
    print("✅ binary files skipped")

def test_review_result_to_dict():
    comment = ReviewComment(
        file="main.py", line=10, severity=Severity.HIGH,
        category=Category.BUG, message="Off-by-one error",
        suggestion="Use < instead of <=", code_fix="for i in range(len(items)):"
    )
    result = ReviewResult(
        pr_title="Test PR", files_reviewed=1, total_lines=50,
        comments=[comment], summary="Found 1 bug.", overall_score=70, approved=False
    )
    d = result.to_dict()
    assert d["comment_counts"]["high"] == 1
    assert d["approved"] == False
    assert d["overall_score"] == 70
    assert len(d["comments"]) == 1
    print("✅ ReviewResult serialises correctly")

def test_parse_malformed_json():
    """Reviewer should handle malformed LLM JSON gracefully."""
    class BadLLM:
        def generate(self, s, u): return "not json at all }{{"
    reviewer = CodeReviewer(BadLLM())
    comments = reviewer.review_file("test.py", "+x = 1", "")
    assert isinstance(comments, list)
    print("✅ malformed JSON handled gracefully")

def test_severity_counts():
    comments = [
        ReviewComment("f.py", 1, Severity.CRITICAL, Category.SECURITY, "msg"),
        ReviewComment("f.py", 2, Severity.CRITICAL, Category.SECURITY, "msg"),
        ReviewComment("f.py", 3, Severity.HIGH,     Category.BUG,      "msg"),
    ]
    result = ReviewResult("PR", 1, 100, comments=comments, summary="", overall_score=10, approved=False)
    assert result.critical_count == 2
    assert result.high_count == 1
    print("✅ severity counts correct")

if __name__ == "__main__":
    tests = [test_review_returns_comments, test_review_approved_clean_code,
             test_skip_binary_files, test_review_result_to_dict,
             test_parse_malformed_json, test_severity_counts]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
