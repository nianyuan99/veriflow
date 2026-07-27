"""审查状态定义 — LangGraph State"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..db.models import (
    ReviewStatus,
    FindingSeverity,
    AgentType,
    FixStatus,
)


@dataclass
class ReviewContext:
    """Phase 1 PREPARE 产物 — 结构化 diff 分析上下文"""
    repo_path: str = ""
    diff_raw: str = ""
    files_changed: list[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    language: str = "unknown"  # python, javascript, go, etc.
    functions_modified: list[str] = field(default_factory=list)
    tree_sitter_ast: dict = field(default_factory=dict)
    semgrep_results: list[dict] = field(default_factory=list)


@dataclass
class FindingData:
    """单个审查发现"""
    id: str = ""
    agent_type: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    severity: str = "P2"
    title: str = ""
    description: str = ""
    suggestion: str = ""
    code_snippet: str = ""
    pattern_id: str | None = None


@dataclass
class FixResult:
    """修复结果"""
    finding_id: str = ""
    attempt_number: int = 1
    status: str = "pending"
    original_code: str = ""
    fixed_code: str = ""
    diff_patch: str = ""
    sandbox_passed: bool = False
    sandbox_output: str = ""
    error_message: str = ""


@dataclass
class ReviewState:
    """LangGraph 全局审查状态"""
    # 标识
    run_id: str = ""
    status: str = "pending"

    # Phase 1: PREPARE
    context: ReviewContext = field(default_factory=ReviewContext)

    # Phase 2: REVIEW
    enabled_agents: list[str] = field(
        default_factory=lambda: ["security", "performance", "logic", "style", "ai_pattern"]
    )
    findings: list[FindingData] = field(default_factory=list)
    deduped_findings: list[FindingData] = field(default_factory=list)

    # Phase 3: FIX + VERIFY
    fix_results: list[FixResult] = field(default_factory=list)
    fix_retry_count: dict[str, int] = field(default_factory=dict)  # finding_id → retry count
    max_retries: int = 3

    # Phase 4: RECORD
    obsidian_synced: bool = False
    obsidian_notes: list[dict] = field(default_factory=list)

    # Meta
    llm_provider: str = "openai"
    llm_model: str = ""
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
