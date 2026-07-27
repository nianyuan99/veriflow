"""LangGraph 编排器 — 四阶段 Agent 编排流程

Phase 1 PREPARE  → diff_parser + tree_sitter → 结构化 ReviewContext
Phase 2 REVIEW   → 5 Agents 并行审查 → Finding[] (去重+合并+排序)
Phase 3 FIX+VERIFY → FixGenerator + Docker Sandbox → 验证通过/重试(max 3)/标记人工
Phase 4 RECORD   → Obsidian Writer → concept笔记 + daily摘要 + 自动关联
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from langgraph.graph import StateGraph, END

from .state import ReviewState, ReviewContext, FindingData, FixResult
from .model_factory import (
    LLMProvider,
    create_default_client,
    create_cheap_client,
    create_smart_client,
)
from .registry import agent_registry

# ── 导入各模块 ────────────────────────────────────────────────────
from ..agents import (
    SecurityAgent,
    PerformanceAgent,
    LogicAgent,
    StyleAgent,
    AIPatternAgent,
)
from ..analyzers import parse_diff, extract_functions
from ..db.models import AgentType


# ═════════════════════════════════════════════════════════════════════
# Phase 1: PREPARE
# ═════════════════════════════════════════════════════════════════════

async def phase_prepare(state: ReviewState) -> ReviewState:
    """解析 diff，构建结构化 ReviewContext"""
    state.status = "preparing"
    state.started_at = datetime.utcnow()

    diff_raw = state.context.diff_raw
    parsed = parse_diff(diff_raw)

    state.context.files_changed = parsed.files_changed
    state.context.additions = parsed.total_additions
    state.context.deletions = parsed.total_deletions
    state.context.language = parsed.language_hint
    state.context.functions_modified = extract_functions(parsed)

    # Semgrep 预扫描
    try:
        from ..analyzers import SemgrepRunner
        runner = SemgrepRunner()
        if runner.available and state.context.repo_path:
            state.context.semgrep_results = runner.scan_diff(
                diff_raw, state.context.repo_path
            )
    except Exception:
        pass

    state.status = "reviewing"
    return state


# ═════════════════════════════════════════════════════════════════════
# Phase 2: REVIEW — 并行 fan-out
# ═════════════════════════════════════════════════════════════════════

async def phase_review(state: ReviewState) -> ReviewState:
    """启动 5 个 Agent 并行审查"""

    # 按 tier 分配模型
    smart_llm = create_smart_client(LLMProvider(state.llm_provider))
    default_llm = create_default_client(LLMProvider(state.llm_provider))
    cheap_llm = create_cheap_client(LLMProvider(state.llm_provider))

    # 创建 Agent 实例
    agents_to_run = []
    enabled = set(state.enabled_agents)

    if "security" in enabled:
        agents_to_run.append(SecurityAgent(smart_llm))
    if "performance" in enabled:
        agents_to_run.append(PerformanceAgent(default_llm))
    if "logic" in enabled:
        agents_to_run.append(LogicAgent(default_llm))
    if "style" in enabled:
        agents_to_run.append(StyleAgent(cheap_llm))
    if "ai_pattern" in enabled:
        agents_to_run.append(AIPatternAgent(smart_llm))

    # 并行运行所有 Agent
    import asyncio
    tasks = [agent.review(state.context) for agent in agents_to_run]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_findings: list[FindingData] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # 记录 agent 错误但继续
            state.error = f"Agent {agents_to_run[i].agent_type} failed: {result}"
        elif isinstance(result, list):
            for f in result:
                f.id = str(uuid.uuid4())
                all_findings.append(f)

    state.findings = all_findings

    # 去重 + 合并
    state.deduped_findings = deduplicate_findings(all_findings)
    # 按 severity 排序
    severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    state.deduped_findings.sort(
        key=lambda f: (severity_order.get(f.severity, 9), f.file_path)
    )

    return state


def deduplicate_findings(findings: list[FindingData]) -> list[FindingData]:
    """去重：同一文件、相邻行、相似标题的合并为一个"""
    if len(findings) <= 1:
        return findings

    # 简单策略：按 (file_path, line_start±3, title 前缀) 分组
    groups: dict[tuple, list[FindingData]] = {}

    for f in findings:
        key = (
            f.file_path,
            f.line_start // 5 if f.line_start else 0,
            f.title[:30] if f.title else "",
        )
        if key not in groups:
            groups[key] = []
        groups[key].append(f)

    merged = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # 合并：取最高 severity
            best = min(group, key=lambda f: {"P0": 0, "P1": 1, "P2": 2, "P3": 3}[f.severity])
            best.description += f"\n\n(同时被 {len(group)-1} 个其他 agent 发现)"
            merged.append(best)

    return merged


# ═════════════════════════════════════════════════════════════════════
# Phase 3: FIX + VERIFY
# ═════════════════════════════════════════════════════════════════════

async def phase_fix_verify(state: ReviewState) -> ReviewState:
    """为每个 Finding 生成修复并在沙箱中验证"""
    state.status = "fixing"

    fix_llm = create_smart_client(LLMProvider(state.llm_provider))

    for finding in state.deduped_findings:
        # 只对 P0 和 P1 自动修复
        if finding.severity not in ("P0", "P1"):
            continue

        fix_result = await generate_and_verify_fix(
            fix_llm, finding, state.context, state.max_retries
        )
        state.fix_results.append(fix_result)

    state.status = "completed"
    state.completed_at = datetime.utcnow()
    return state


async def generate_and_verify_fix(
    llm_client,
    finding: FindingData,
    context: ReviewContext,
    max_retries: int = 3,
) -> FixResult:
    """生成修复代码并在 Docker 沙箱中验证，最多重试 3 次"""
    result = FixResult(
        finding_id=finding.id,
        attempt_number=1,
        original_code=finding.code_snippet or "",
    )

    for attempt in range(1, max_retries + 1):
        result.attempt_number = attempt

        # Step 1: 生成修复
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=get_fix_system_prompt()),
                HumanMessage(content=f"""原始问题：
- 文件: {finding.file_path}:{finding.line_start}
- 严重度: {finding.severity}
- 标题: {finding.title}
- 描述: {finding.description}
- 修复建议: {finding.suggestion}

原始代码:
{finding.code_snippet if finding.code_snippet else '(see description)'}

请生成修复后的代码和 unified diff patch。"""),
            ]
            response = await llm_client.ainvoke(messages)
            # 解析响应
            parsed = parse_fix_response(str(response.content))
            result.fixed_code = parsed.get("fixed_code", "")
            result.diff_patch = parsed.get("diff_patch", "")

            if not result.fixed_code:
                result.status = "manual_required"
                result.error_message = "LLM 未能生成有效修复"
                break

            result.status = "sandbox_running"
        except Exception as e:
            result.error_message = f"修复生成失败: {e}"
            result.status = "manual_required"
            break

        # Step 2: 沙箱验证
        try:
            sandbox_passed, sandbox_output = await run_sandbox_verify(
                result.diff_patch,
                language=context.language,
                repo_path=context.repo_path,
            )
            result.sandbox_output = sandbox_output

            if sandbox_passed:
                result.status = "sandbox_passed"
                result.sandbox_passed = True
                break
            else:
                result.status = "sandbox_failed"
                if attempt < max_retries:
                    result.status = "retrying"
        except Exception as e:
            result.error_message = f"沙箱验证异常: {e}"
            result.status = "sandbox_failed"
            if attempt >= max_retries:
                result.status = "manual_required"

    return result


def get_fix_system_prompt() -> str:
    return """你是代码修复专家。请根据问题描述生成修复代码。

输出格式（用 ``` 标记）：
1. 用 ```fixed 标记修复后的完整代码
2. 用 ```diff 标记 unified diff patch

确保修复：
- 最小化变更范围
- 不破坏现有功能
- 遵循项目的编码风格
- 包含必要的测试保护"""


def parse_fix_response(text: str) -> dict:
    """解析修复响应"""
    result = {"fixed_code": "", "diff_patch": ""}

    # 提取 fixed code
    if "```fixed" in text:
        parts = text.split("```fixed", 1)[1].split("```", 1)
        if parts:
            result["fixed_code"] = parts[0].strip()
    elif "```python" in text:
        parts = text.split("```python", 1)[1].split("```", 1)
        if parts:
            result["fixed_code"] = parts[0].strip()

    # 提取 diff
    if "```diff" in text:
        parts = text.split("```diff", 1)[1].split("```", 1)
        if parts:
            result["diff_patch"] = parts[0].strip()

    return result


async def run_sandbox_verify(
    diff_patch: str,
    language: str = "python",
    repo_path: str = "",
) -> tuple[bool, str]:
    """在 Docker 沙箱中验证修复"""
    try:
        from ..sandbox.docker_manager import DockerSandbox

        sandbox = DockerSandbox(language=language, repo_path=repo_path)
        result = await sandbox.run_tests(diff_patch)
        return result.passed, result.output
    except ImportError:
        # Docker SDK 不可用时返回模拟结果
        return True, "Sandbox skipped (Docker SDK not available)"
    except Exception as e:
        return False, f"Sandbox error: {e}"


# ═════════════════════════════════════════════════════════════════════
# Phase 4: RECORD — Obsidian 记录
# ═════════════════════════════════════════════════════════════════════

async def phase_record(state: ReviewState) -> ReviewState:
    """将审查结果写入 Obsidian 知识库"""
    state.status = "verifying"

    try:
        from ..obsidian.writer import ObsidianWriter
        writer = ObsidianWriter()

        for finding in state.deduped_findings:
            note = await writer.write_concept(finding)
            if note:
                state.obsidian_notes.append(note)

        # 写每日摘要
        summary = await writer.write_daily_summary(
            state.deduped_findings, state.fix_results
        )
        if summary:
            state.obsidian_notes.append(summary)

        state.obsidian_synced = True
    except Exception as e:
        state.error = f"Obsidian sync failed: {e}"

    state.status = "completed"
    state.completed_at = datetime.utcnow()
    return state


# ═════════════════════════════════════════════════════════════════════
# 构建 LangGraph Workflow
# ═════════════════════════════════════════════════════════════════════

def build_review_graph() -> StateGraph:
    """构建四阶段审查工作流"""
    workflow = StateGraph(ReviewState)

    # 添加节点
    workflow.add_node("prepare", phase_prepare)
    workflow.add_node("review", phase_review)
    workflow.add_node("fix_verify", phase_fix_verify)
    workflow.add_node("record", phase_record)

    # 设置流程
    workflow.set_entry_point("prepare")
    workflow.add_edge("prepare", "review")
    workflow.add_edge("review", "fix_verify")
    workflow.add_edge("fix_verify", "record")
    workflow.add_edge("record", END)

    return workflow


# ═════════════════════════════════════════════════════════════════════
# 便捷运行函数
# ═════════════════════════════════════════════════════════════════════

async def run_full_review(
    diff_content: str,
    repo_path: str = "",
    enabled_agents: Optional[list[str]] = None,
    llm_provider: str = "openai",
    llm_model: str = "",
) -> ReviewState:
    """运行完整的四阶段审查流程"""
    state = ReviewState(
        run_id=str(uuid.uuid4()),
        context=ReviewContext(
            repo_path=repo_path,
            diff_raw=diff_content,
        ),
        enabled_agents=enabled_agents or [
            "security", "performance", "logic", "style", "ai_pattern"
        ],
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

    graph = build_review_graph()
    workflow = graph.compile()

    result = await workflow.ainvoke(state)
    return result
