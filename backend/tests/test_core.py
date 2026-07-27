"""VerifyFlow 后端测试"""

import pytest
from pathlib import Path
import sys

# 确保能找到包
sys.path.insert(0, str(Path(__file__).parent))

from verifyflow_server.analyzers.diff_parser import parse_diff, extract_functions
from verifyflow_server.core.state import ReviewState, ReviewContext, FindingData
from verifyflow_server.core.model_factory import (
    LLMProvider, LLMConfig, get_model_for_tier, PROVIDER_DEFAULTS
)
from verifyflow_server.db.models import (
    ReviewStatus, FindingSeverity, AgentType, FixStatus,
    ReviewRun, Finding, FixAttempt, SandboxResult, ObsidianNote, BenchmarkRun
)


class TestDiffParser:
    """Diff 解析器测试"""

    def test_parse_basic_diff(self):
        diff = """diff --git a/app/main.py b/app/main.py
--- a/app/main.py
+++ b/app/main.py
@@ -10,6 +10,8 @@ def get_user(user_id):
+def search(query):
+    sql = f"SELECT * FROM users WHERE name = '{query}'"
+    return db.execute(sql)"""

        parsed = parse_diff(diff)
        assert len(parsed.files) == 1
        assert parsed.files[0].new_path == "app/main.py"
        assert parsed.total_additions == 3
        assert parsed.total_deletions == 0
        assert parsed.language_hint == "python"

    def test_parse_empty_diff(self):
        parsed = parse_diff("")
        assert len(parsed.files) == 0

    def test_parse_multi_file_diff(self):
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
+new line
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,1 @@
-old
+new"""

        parsed = parse_diff(diff)
        assert len(parsed.files) == 2
        assert parsed.files_changed == ["a.py", "b.py"]

    def test_extract_functions(self):
        diff = """diff --git a/app.py b/app.py
+def new_function():
+    pass
-def old_function():
-    pass
+async def async_new():
+    pass"""

        funcs = extract_functions(parse_diff(diff))
        assert "new_function" in funcs
        assert "old_function" in funcs
        assert "async_new" in funcs


class TestModelFactory:
    """LLM 工厂测试"""

    def test_get_model_for_tier(self):
        model = get_model_for_tier(LLMProvider.OPENAI, "cheap")
        assert model == "gpt-4o-mini"

        model = get_model_for_tier(LLMProvider.OPENAI, "default")
        assert model == "gpt-4o"

    def test_provider_defaults_complete(self):
        for provider in LLMProvider:
            defaults = PROVIDER_DEFAULTS.get(provider)
            if defaults:
                assert "cheap" in defaults
                assert "default" in defaults
                assert "smart" in defaults


class TestReviewState:
    """审查状态测试"""

    def test_default_state(self):
        state = ReviewState()
        assert state.status == "pending"
        assert len(state.enabled_agents) == 5
        assert "security" in state.enabled_agents

    def test_context_defaults(self):
        ctx = ReviewContext()
        assert ctx.diff_raw == ""
        assert ctx.files_changed == []
        assert ctx.language == "unknown"


class TestDBModels:
    """数据库模型测试"""

    def test_review_status_enum(self):
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.COMPLETED.value == "completed"

    def test_finding_severity_enum(self):
        assert FindingSeverity.P0.value == "P0"
        assert FindingSeverity.P3.value == "P3"

    def test_agent_type_enum(self):
        assert AgentType.SECURITY.value == "security"
        assert AgentType.AI_PATTERN.value == "ai_pattern"

    def test_fix_status_enum(self):
        assert FixStatus.PENDING.value == "pending"
        assert FixStatus.SANDBOX_PASSED.value == "sandbox_passed"
