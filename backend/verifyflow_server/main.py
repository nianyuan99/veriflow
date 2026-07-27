"""VerifyFlow FastAPI 应用"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.orchestrator import run_full_review
from .core.state import ReviewState
from .db import (
    get_engine,
    create_tables,
    get_session,
    create_review_run,
    get_review_run,
    update_review_run_status,
    finish_review_run,
    create_finding,
    get_findings_by_run,
    create_fix_attempt,
    update_fix_attempt,
    create_sandbox_result,
    create_obsidian_note,
    create_benchmark_run,
    update_benchmark_results,
)
from .db.models import ReviewStatus
from .benchmark.runner import BenchmarkRunner, build_default_cases
from .analyzers import parse_diff


# ── App 生命周期 ──────────────────────────────────────────────────

engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = get_engine()
    create_tables(engine)
    # 构建默认 benchmark 用例
    import os
    cases_dir = os.path.join(os.path.dirname(__file__), "benchmark", "cases")
    build_default_cases(cases_dir)
    yield


app = FastAPI(
    title="VerifyFlow API",
    description="AI Code Review Agent + Sandbox Verify + Obsidian Sync",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求模型 ──────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    diff_content: str
    repo_path: str = ""
    branch_name: str | None = None
    pr_title: str | None = None
    llm_provider: str = "openai"
    llm_model: str = ""
    enabled_agents: list[str] | None = None


class FixRequest(BaseModel):
    finding_id: str


class SandboxRequest(BaseModel):
    fix_attempt_id: str
    diff_patch: str
    language: str = "python"


class ObsidianSyncRequest(BaseModel):
    review_run_id: str


class BenchmarkRequest(BaseModel):
    name: str = "default"
    llm_model: str = ""


# ── REST API Endpoints ────────────────────────────────────────────


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# ── Review ────────────────────────────────────────────────────────


@app.post("/api/v1/review")
async def submit_review(req: ReviewRequest):
    """提交代码审查"""
    session = get_session(engine)

    try:
        # 创建 review run
        run = create_review_run(
            session=session,
            repo_path=req.repo_path,
            diff_content=req.diff_content,
            branch_name=req.branch_name,
            pr_title=req.pr_title,
            llm_model=req.llm_model or req.llm_provider,
        )

        # 运行审查
        state = await run_full_review(
            diff_content=req.diff_content,
            repo_path=req.repo_path,
            enabled_agents=req.enabled_agents,
            llm_provider=req.llm_provider,
            llm_model=req.llm_model,
        )

        # 持久化 findings
        for f in state.deduped_findings:
            create_finding(
                session=session,
                review_run_id=run.id,
                agent_type=f.agent_type,
                file_path=f.file_path,
                severity=f.severity,
                title=f.title,
                description=f.description,
                suggestion=f.suggestion,
                code_snippet=f.code_snippet,
                pattern_id=f.pattern_id,
                line_start=f.line_start,
                line_end=f.line_end,
            )

        # 持久化 fix attempts
        for fix in state.fix_results:
            attempt = create_fix_attempt(
                session=session,
                review_run_id=run.id,
                finding_id=fix.finding_id,
            )
            update_fix_attempt(
                session=session,
                attempt=attempt,
                status=fix.status,
                fixed_code=fix.fixed_code,
                diff_patch=fix.diff_patch,
                error_message=fix.error_message,
            )

        # 完成
        finish_review_run(session, run)

        return {
            "run_id": run.id,
            "status": run.status.value,
            "total_findings": run.total_findings,
            "p0_count": run.p0_count,
            "p1_count": run.p1_count,
            "p2_count": run.p2_count,
            "p3_count": run.p3_count,
            "findings": [
                {
                    "id": f.id,
                    "agent_type": f.agent_type.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                }
                for f in run.findings
            ],
        }

    finally:
        session.close()


@app.get("/api/v1/review/{run_id}")
async def get_review_detail(run_id: str):
    """获取审查详情"""
    session = get_session(engine)
    try:
        run = get_review_run(session, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Review run not found")

        return {
            "run_id": run.id,
            "status": run.status.value,
            "repo_path": run.repo_path,
            "branch_name": run.branch_name,
            "pr_title": run.pr_title,
            "total_findings": run.total_findings,
            "p0_count": run.p0_count,
            "p1_count": run.p1_count,
            "p2_count": run.p2_count,
            "p3_count": run.p3_count,
            "total_fix_attempts": run.total_fix_attempts,
            "fix_success_rate": run.fix_success_rate,
            "llm_model": run.llm_model,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "findings": [
                {
                    "id": f.id,
                    "agent_type": f.agent_type.value,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "suggestion": f.suggestion,
                    "code_snippet": f.code_snippet,
                    "pattern_id": f.pattern_id,
                    "is_fixed": f.is_fixed,
                }
                for f in run.findings
            ],
            "fix_attempts": [
                {
                    "id": a.id,
                    "finding_id": a.finding_id,
                    "attempt_number": a.attempt_number,
                    "status": a.status.value,
                    "original_code": a.original_code,
                    "fixed_code": a.fixed_code,
                    "diff_patch": a.diff_patch,
                    "error_message": a.error_message,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                }
                for a in run.fix_attempts
            ],
        }
    finally:
        session.close()


@app.get("/api/v1/findings")
async def list_findings(
    run_id: str | None = None,
    severity: str | None = None,
    agent_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """全局发现列表 (支持筛选)"""
    session = get_session(engine)
    try:
        from .db.models import Finding, FindingSeverity, AgentType

        query = session.query(Finding)

        if run_id:
            query = query.filter(Finding.review_run_id == run_id)
        if severity:
            query = query.filter(Finding.severity == FindingSeverity(severity))
        if agent_type:
            query = query.filter(Finding.agent_type == AgentType(agent_type))

        total = query.count()
        findings = (
            query.order_by(Finding.severity, Finding.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "findings": [
                {
                    "id": f.id,
                    "review_run_id": f.review_run_id,
                    "agent_type": f.agent_type.value,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "is_fixed": f.is_fixed,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in findings
            ],
        }
    finally:
        session.close()


# ── Benchmark ─────────────────────────────────────────────────────


@app.post("/api/v1/bench/run")
async def run_benchmark(req: BenchmarkRequest):
    """运行 benchmark"""
    session = get_session(engine)
    try:
        # 创建 benchmark run
        bench_run = create_benchmark_run(
            session=session,
            name=req.name,
            llm_model=req.llm_model,
        )

        runner = BenchmarkRunner()
        runner.load_cases()

        async def review_fn(diff_content: str):
            from .core.state import ReviewState, ReviewContext
            from .core.orchestrator import phase_prepare, phase_review

            state = ReviewState(
                context=ReviewContext(diff_raw=diff_content),
                llm_provider="openai",
            )
            state = await phase_prepare(state)
            state = await phase_review(state)
            return state.deduped_findings

        report = runner.run(review_fn)

        # 持久化结果
        import json
        update_benchmark_results(
            session=session,
            run=bench_run,
            total_cases=report.total_cases,
            true_positives=report.total_tp,
            false_positives=report.total_fp,
            false_negatives=report.total_fn,
            case_results=json.dumps(report.to_dict()),
        )

        return report.to_dict()

    finally:
        session.close()


# ── Obsidian Sync ─────────────────────────────────────────────────


@app.post("/api/v1/obsidian/sync")
async def sync_to_obsidian(req: ObsidianSyncRequest):
    """同步审查结果到 Obsidian"""
    session = get_session(engine)
    try:
        run = get_review_run(session, req.review_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Review run not found")

        from .obsidian import ObsidianWriter
        writer = ObsidianWriter()

        notes_created = 0
        for finding in run.findings:
            note_data = await writer.write_concept(finding)
            if note_data:
                create_obsidian_note(
                    session=session,
                    finding_id=finding.id,
                    note_type="concept",
                    vault_path=note_data["vault_path"],
                    file_name=note_data["file_name"],
                    title=note_data["title"],
                    content=note_data["content"],
                )
                notes_created += 1

        return {
            "status": "synced",
            "review_run_id": req.review_run_id,
            "notes_created": notes_created,
        }

    finally:
        session.close()


# ── WebSocket ─────────────────────────────────────────────────────


@app.websocket("/ws/review/{run_id}")
async def review_websocket(websocket: WebSocket, run_id: str):
    """WebSocket 实时推送审查进度"""
    await websocket.accept()
    try:
        session = get_session(engine)
        run = get_review_run(session, run_id)
        if run:
            await websocket.send_json({
                "type": "status",
                "run_id": run_id,
                "status": run.status.value,
            })
        session.close()

        # 轮询状态 (简化方案)
        import asyncio
        while True:
            await asyncio.sleep(2)
            session = get_session(engine)
            run = get_review_run(session, run_id)
            if run:
                await websocket.send_json({
                    "type": "status",
                    "run_id": run_id,
                    "status": run.status.value,
                    "total_findings": run.total_findings,
                    "fix_success_rate": run.fix_success_rate,
                })
                if run.status == ReviewStatus.COMPLETED:
                    break
            session.close()

        await websocket.send_json({"type": "complete", "run_id": run_id})
    except WebSocketDisconnect:
        pass


# ── Settings ──────────────────────────────────────────────────────


@app.get("/api/v1/settings")
async def get_settings():
    """获取当前配置"""
    import os
    return {
        "llm_providers": ["openai", "anthropic", "deepseek"],
        "available_agents": [
            "security", "performance", "logic", "style", "ai_pattern"
        ],
        "obsidian_enabled": os.path.isdir(r"C:\knowledge base\wiki"),
        "docker_available": _check_docker(),
    }


def _check_docker() -> bool:
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False
