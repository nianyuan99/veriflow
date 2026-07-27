"""数据访问层 — Repository 模式"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import (
    ReviewRun,
    Finding,
    FixAttempt,
    SandboxResult,
    ObsidianNote,
    BenchmarkRun,
    ReviewStatus,
)


# ── ReviewRun ──────────────────────────────────────────────────────

def create_review_run(
    session: Session,
    repo_path: str | None = None,
    diff_content: str | None = None,
    branch_name: str | None = None,
    pr_title: str | None = None,
    llm_model: str | None = None,
) -> ReviewRun:
    run = ReviewRun(
        id=str(uuid.uuid4()),
        repo_path=repo_path,
        diff_content=diff_content,
        branch_name=branch_name,
        pr_title=pr_title,
        llm_model=llm_model,
    )
    session.add(run)
    session.commit()
    return run


def get_review_run(session: Session, run_id: str) -> ReviewRun | None:
    return session.get(ReviewRun, run_id)


def update_review_run_status(
    session: Session, run: ReviewRun, status: ReviewStatus
):
    run.status = status
    run.updated_at = datetime.utcnow()
    session.commit()


def finish_review_run(session: Session, run: ReviewRun):
    """汇总统计数据并标记完成"""
    findings = run.findings
    run.total_findings = len(findings)
    run.p0_count = sum(1 for f in findings if f.severity.value == "P0")
    run.p1_count = sum(1 for f in findings if f.severity.value == "P1")
    run.p2_count = sum(1 for f in findings if f.severity.value == "P2")
    run.p3_count = sum(1 for f in findings if f.severity.value == "P3")

    fixes = run.fix_attempts
    run.total_fix_attempts = len(fixes)
    if fixes:
        passed = sum(
            1 for f in fixes if f.status.value == "sandbox_passed"
        )
        run.fix_success_rate = passed / len(fixes)

    run.status = ReviewStatus.COMPLETED
    run.updated_at = datetime.utcnow()
    session.commit()


# ── Finding ────────────────────────────────────────────────────────

def create_finding(
    session: Session,
    review_run_id: str,
    agent_type: str,
    file_path: str,
    severity: str,
    title: str,
    description: str,
    suggestion: str | None = None,
    code_snippet: str | None = None,
    pattern_id: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
) -> Finding:
    from .models import AgentType, FindingSeverity

    finding = Finding(
        id=str(uuid.uuid4()),
        review_run_id=review_run_id,
        agent_type=AgentType(agent_type),
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        severity=FindingSeverity(severity),
        title=title,
        description=description,
        suggestion=suggestion,
        code_snippet=code_snippet,
        pattern_id=pattern_id,
    )
    session.add(finding)
    session.commit()
    return finding


def get_findings_by_run(session: Session, run_id: str) -> list[Finding]:
    return (
        session.query(Finding)
        .filter(Finding.review_run_id == run_id)
        .order_by(Finding.severity)
        .all()
    )


# ── FixAttempt ─────────────────────────────────────────────────────

def create_fix_attempt(
    session: Session,
    review_run_id: str,
    finding_id: str,
    attempt_number: int = 1,
    original_code: str | None = None,
) -> FixAttempt:
    attempt = FixAttempt(
        id=str(uuid.uuid4()),
        review_run_id=review_run_id,
        finding_id=finding_id,
        attempt_number=attempt_number,
        original_code=original_code,
    )
    session.add(attempt)
    session.commit()
    return attempt


def update_fix_attempt(
    session: Session,
    attempt: FixAttempt,
    status: str | None = None,
    fixed_code: str | None = None,
    diff_patch: str | None = None,
    validation_output: str | None = None,
    error_message: str | None = None,
):
    from .models import FixStatus

    if status:
        attempt.status = FixStatus(status)
    if fixed_code is not None:
        attempt.fixed_code = fixed_code
    if diff_patch is not None:
        attempt.diff_patch = diff_patch
    if validation_output is not None:
        attempt.validation_output = validation_output
    if error_message is not None:
        attempt.error_message = error_message
    if status in ("sandbox_passed", "sandbox_failed", "manual_required"):
        attempt.completed_at = datetime.utcnow()
    session.commit()


# ── SandboxResult ──────────────────────────────────────────────────

def create_sandbox_result(
    session: Session,
    fix_attempt_id: str,
    language: str,
    image_used: str,
    tests_passed: int = 0,
    tests_failed: int = 0,
    tests_total: int = 0,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    duration_ms: int | None = None,
) -> SandboxResult:
    result = SandboxResult(
        id=str(uuid.uuid4()),
        fix_attempt_id=fix_attempt_id,
        language=language,
        image_used=image_used,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        tests_total=tests_total,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
    )
    session.add(result)
    session.commit()
    return result


# ── ObsidianNote ───────────────────────────────────────────────────

def create_obsidian_note(
    session: Session,
    finding_id: str,
    note_type: str,
    vault_path: str,
    file_name: str,
    title: str,
    content: str,
    wikilinks: list[str] | None = None,
    tags: list[str] | None = None,
) -> ObsidianNote:
    import json

    note = ObsidianNote(
        id=str(uuid.uuid4()),
        finding_id=finding_id,
        note_type=note_type,
        vault_path=vault_path,
        file_name=file_name,
        title=title,
        content=content,
        wikilinks=json.dumps(wikilinks) if wikilinks else None,
        tags=json.dumps(tags) if tags else None,
    )
    session.add(note)
    session.commit()
    return note


# ── BenchmarkRun ───────────────────────────────────────────────────

def create_benchmark_run(
    session: Session,
    name: str,
    description: str | None = None,
    llm_model: str | None = None,
) -> BenchmarkRun:
    run = BenchmarkRun(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        llm_model=llm_model,
    )
    session.add(run)
    session.commit()
    return run


def update_benchmark_results(
    session: Session,
    run: BenchmarkRun,
    total_cases: int,
    true_positives: int,
    false_positives: int,
    false_negatives: int,
    case_results: str,
):
    run.total_cases = total_cases
    run.true_positives = true_positives
    run.false_positives = false_positives
    run.false_negatives = false_negatives

    tp, fp, fn = true_positives, false_positives, false_negatives
    run.precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    run.recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if run.precision and run.recall and (run.precision + run.recall) > 0:
        run.f1_score = (
            2 * run.precision * run.recall / (run.precision + run.recall)
        )
    else:
        run.f1_score = 0.0

    run.case_results = case_results
    session.commit()
