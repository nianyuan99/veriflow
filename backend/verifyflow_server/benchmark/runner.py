"""Benchmark Runner — 代码审查质量评估

支持 precision/recall/F1 评分
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BenchmarkCase:
    """单个 Benchmark 测试用例"""
    id: str
    name: str
    description: str
    language: str
    diff_content: str
    expected_findings: list[dict]  # 预期应该发现的问题
    min_severity: str = "P3"  # 最低应报告的严重度


@dataclass
class BenchmarkResult:
    """Benchmark 运行结果"""
    case_id: str
    case_name: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    details: list[dict] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    """完整 Benchmark 报告"""
    name: str
    total_cases: int
    results: list[BenchmarkResult] = field(default_factory=list)

    @property
    def avg_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision for r in self.results) / len(self.results)

    @property
    def avg_recall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.recall for r in self.results) / len(self.results)

    @property
    def avg_f1(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.f1_score for r in self.results) / len(self.results)

    @property
    def total_tp(self) -> int:
        return sum(r.true_positives for r in self.results)

    @property
    def total_fp(self) -> int:
        return sum(r.false_positives for r in self.results)

    @property
    def total_fn(self) -> int:
        return sum(r.false_negatives for r in self.results)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_cases": self.total_cases,
            "avg_precision": round(self.avg_precision, 4),
            "avg_recall": round(self.avg_recall, 4),
            "avg_f1": round(self.avg_f1, 4),
            "total_tp": self.total_tp,
            "total_fp": self.total_fp,
            "total_fn": self.total_fn,
            "results": [
                {
                    "case_id": r.case_id,
                    "case_name": r.case_name,
                    "true_positives": r.true_positives,
                    "false_positives": r.false_positives,
                    "false_negatives": r.false_negatives,
                    "precision": round(r.precision, 4),
                    "recall": round(r.recall, 4),
                    "f1_score": round(r.f1_score, 4),
                }
                for r in self.results
            ],
        }


class BenchmarkRunner:
    """Benchmark 运行器"""

    def __init__(self, cases_dir: str = ""):
        self.cases_dir = cases_dir or os.path.join(
            os.path.dirname(__file__), "cases"
        )
        self.cases: list[BenchmarkCase] = []

    def load_cases(self) -> list[BenchmarkCase]:
        """从 cases/ 目录加载 Benchmark 用例"""
        self.cases = []

        if not os.path.isdir(self.cases_dir):
            return self.cases

        for fname in sorted(os.listdir(self.cases_dir)):
            if fname.endswith(".json") and fname != "manifest.json":
                path = os.path.join(self.cases_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    case = BenchmarkCase(
                        id=data.get("id", fname),
                        name=data.get("name", fname),
                        description=data.get("description", ""),
                        language=data.get("language", "python"),
                        diff_content=data.get("diff_content", ""),
                        expected_findings=data.get("expected_findings", []),
                        min_severity=data.get("min_severity", "P3"),
                    )
                    self.cases.append(case)
                except Exception as e:
                    print(f"Failed to load benchmark case {fname}: {e}")

        return self.cases

    def run(self, review_fn) -> BenchmarkReport:
        """运行 benchmark

        review_fn: async (diff_content: str) → list[FindingData]
        """
        if not self.cases:
            self.load_cases()

        report = BenchmarkReport(
            name=f"Benchmark-{uuid.uuid4().hex[:8]}",
            total_cases=len(self.cases),
        )

        for case in self.cases:
            result = self.measure_case(case, review_fn)
            report.results.append(result)

        return report

    def measure_case(
        self,
        case: BenchmarkCase,
        review_fn,
    ) -> BenchmarkResult:
        """对单个 case 计算 precision/recall"""
        import asyncio

        # 运行审查
        loop = asyncio.new_event_loop()
        found = loop.run_until_complete(review_fn(case.diff_content))
        loop.close()

        result = BenchmarkResult(
            case_id=case.id,
            case_name=case.name,
        )

        expected_titles = {e["title"] for e in case.expected_findings}
        found_titles = {f.title for f in found} if found else set()

        # 匹配 (使用可变标题匹配)
        matched_expected = set()
        matched_found = set()

        for e in case.expected_findings:
            for f in found:
                if f.title in matched_found:
                    continue
                # 简单模糊匹配
                if (
                    e["title"].lower()[:20] in f.title.lower()
                    or f.title.lower()[:20] in e["title"].lower()
                    or e.get("pattern_id") and e["pattern_id"] == f.pattern_id
                ):
                    matched_expected.add(e["title"])
                    matched_found.add(f.title)
                    result.details.append({
                        "expected": e["title"],
                        "found": f.title,
                        "match": True,
                    })
                    break

        result.true_positives = len(matched_expected)
        result.false_positives = len(found_titles - matched_found)
        result.false_negatives = len(expected_titles - matched_expected)

        tp, fp, fn = result.true_positives, result.false_positives, result.false_negatives
        result.precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        result.recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if result.precision + result.recall > 0:
            result.f1_score = (
                2 * result.precision * result.recall
                / (result.precision + result.recall)
            )

        return result


def build_default_cases(cases_dir: str):
    """构建 10+ 个默认 benchmark 用例"""
    os.makedirs(cases_dir, exist_ok=True)

    cases = [
        {
            "id": "sql-injection-01",
            "name": "SQL Injection — String Concatenation",
            "description": "检测基本的 SQL 注入模式（f-string 拼接 SQL）",
            "language": "python",
            "diff_content": """diff --git a/app/db.py b/app/db.py
--- a/app/db.py
+++ b/app/db.py
@@ -10,6 +10,8 @@ def get_user(user_id):
+def search_users(keyword):
+    query = f"SELECT * FROM users WHERE name LIKE '%{keyword}%'"
+    return db.execute(query).fetchall()""",
            "expected_findings": [
                {
                    "title": "SQL Injection — f-string query construction",
                    "pattern_id": "sql-injection-fstring",
                    "severity": "P0",
                }
            ],
        },
        {
            "id": "xss-01",
            "name": "XSS — innerHTML Injection",
            "description": "检测危险的 innerHTML 使用",
            "language": "javascript",
            "diff_content": """diff --git a/src/ui.js b/src/ui.js
--- a/src/ui.js
+++ b/src/ui.js
@@ -5,6 +5,8 @@ function displayMessage(msg) {
+function renderUserContent(userHtml) {
+    document.getElementById('content').innerHTML = userHtml;
+}""",
            "expected_findings": [
                {
                    "title": "XSS — unsafe innerHTML assignment",
                    "pattern_id": "xss-innerhtml",
                    "severity": "P0",
                }
            ],
        },
        {
            "id": "hardcoded-secret-01",
            "name": "Hardcoded API Key",
            "description": "检测代码中硬编码的 API 密钥",
            "language": "python",
            "diff_content": """diff --git a/app/config.py b/app/config.py
--- a/app/config.py
+++ b/app/config.py
@@ -1,3 +1,5 @@
+OPENAI_API_KEY = "sk-proj-abc123def456ghi789jkl"
+STRIPE_SECRET = "sk_live_xyz789"
 DEBUG = True""",
            "expected_findings": [
                {
                    "title": "Hardcoded API key in source code",
                    "pattern_id": "hardcoded-secret",
                    "severity": "P0",
                }
            ],
        },
        {
            "id": "nplus1-01",
            "name": "N+1 Query in Loop",
            "description": "检测循环中的数据库查询",
            "language": "python",
            "diff_content": """diff --git a/app/api.py b/app/api.py
--- a/app/api.py
+++ b/app/api.py
@@ -5,6 +5,9 @@ def get_orders():
+def get_user_orders(user_ids):
+    for uid in user_ids:
+        orders = db.query("SELECT * FROM orders WHERE user_id = ?", uid)
+        results.append(orders)""",
            "expected_findings": [
                {
                    "title": "N+1 query — loop query pattern",
                    "pattern_id": "nplus1-query",
                    "severity": "P1",
                }
            ],
        },
        {
            "id": "null-pointer-01",
            "name": "Null Reference Check Missing",
            "description": "检测缺少空值检查的代码",
            "language": "python",
            "diff_content": """diff --git a/app/utils.py b/app/utils.py
--- a/app/utils.py
+++ b/app/utils.py
@@ -3,6 +3,8 @@ def process(data):
+def get_name_length(user):
+    return len(user.name)""",
            "expected_findings": [
                {
                    "title": "Missing None check — potential AttributeError",
                    "pattern_id": "null-check-missing",
                    "severity": "P2",
                }
            ],
        },
        {
            "id": "command-injection-01",
            "name": "Command Injection via subprocess",
            "description": "检测 Shell 命令注入",
            "language": "python",
            "diff_content": """diff --git a/app/tools.py b/app/tools.py
--- a/app/tools.py
+++ b/app/tools.py
@@ -1,3 +1,6 @@
+import os
+def run_scan(target):
+    os.system(f"nmap {target}")""",
            "expected_findings": [
                {
                    "title": "Command injection — os.system with user input",
                    "pattern_id": "command-injection",
                    "severity": "P0",
                }
            ],
        },
        {
            "id": "path-traversal-01",
            "name": "Path Traversal in File Read",
            "description": "检测路径遍历漏洞",
            "language": "python",
            "diff_content": """diff --git a/app/files.py b/app/files.py
--- a/app/files.py
+++ b/app/files.py
@@ -2,6 +2,8 @@ import os
+def read_user_file(filename):
+    path = os.path.join('/var/data', filename)
+    return open(path).read()
""",
            "expected_findings": [
                {
                    "title": "Path traversal — unvalidated user filename",
                    "pattern_id": "path-traversal",
                    "severity": "P0",
                }
            ],
        },
        {
            "id": "race-condition-01",
            "name": "Race Condition — Shared State",
            "description": "检测竞态条件",
            "language": "python",
            "diff_content": """diff --git a/app/counter.py b/app/counter.py
--- a/app/counter.py
+++ b/app/counter.py
@@ -3,6 +3,10 @@ counter = 0
+def increment():
+    global counter
+    current = counter
+    counter = current + 1
+    return counter""",
            "expected_findings": [
                {
                    "title": "Race condition — non-atomic increment",
                    "pattern_id": "race-condition",
                    "severity": "P1",
                }
            ],
        },
        {
            "id": "memory-leak-01",
            "name": "Memory Leak — Unclosed Resource",
            "description": "检测未关闭的文件句柄",
            "language": "python",
            "diff_content": """diff --git a/app/reader.py b/app/reader.py
--- a/app/reader.py
+++ b/app/reader.py
@@ -1,3 +1,7 @@
+def read_all(paths):
+    results = []
+    for p in paths:
+        results.append(open(p).read())
+    return results""",
            "expected_findings": [
                {
                    "title": "Resource leak — file handle not closed",
                    "pattern_id": "resource-leak",
                    "severity": "P2",
                }
            ],
        },
        {
            "id": "except-pass-01",
            "name": "Swallowed Exception",
            "description": "检测被静默吞掉的异常",
            "language": "python",
            "diff_content": """diff --git a/app/handler.py b/app/handler.py
--- a/app/handler.py
+++ b/app/handler.py
@@ -2,6 +2,10 @@ import json
+def parse_config(raw):
+    try:
+        return json.loads(raw)
+    except:
+        pass""",
            "expected_findings": [
                {
                    "title": "Bare except clause swallows all exceptions",
                    "pattern_id": "bare-except",
                    "severity": "P2",
                }
            ],
        },
    ]

    for case in cases:
        path = os.path.join(cases_dir, f"{case['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2, ensure_ascii=False)

    return cases
