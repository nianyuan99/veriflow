"""VerifyFlow 数据库模型 — 6 张核心表"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session


class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────────────────

class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    REVIEWING = "reviewing"
    FIXING = "fixing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(str, enum.Enum):
    P0 = "P0"  # Critical / Security
    P1 = "P1"  # High
    P2 = "P2"  # Medium
    P3 = "P3"  # Low / Style


class FixStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    SANDBOX_RUNNING = "sandbox_running"
    SANDBOX_PASSED = "sandbox_passed"
    SANDBOX_FAILED = "sandbox_failed"
    RETRYING = "retrying"
    MANUAL_REQUIRED = "manual_required"


class AgentType(str, enum.Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    STYLE = "style"
    AI_PATTERN = "ai_pattern"


# ── Models ─────────────────────────────────────────────────────────

class ReviewRun(Base):
    __tablename__ = "review_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    repo_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pr_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    p0_count: Mapped[int] = mapped_column(Integer, default=0)
    p1_count: Mapped[int] = mapped_column(Integer, default=0)
    p2_count: Mapped[int] = mapped_column(Integer, default=0)
    p3_count: Mapped[int] = mapped_column(Integer, default=0)

    total_fix_attempts: Mapped[int] = mapped_column(Integer, default=0)
    fix_success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="review_run", cascade="all, delete-orphan"
    )
    fix_attempts: Mapped[list["FixAttempt"]] = relationship(
        back_populates="review_run", cascade="all, delete-orphan"
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_runs.id"), index=True
    )
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType))

    file_path: Mapped[str] = mapped_column(String(500))
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    severity: Mapped[FindingSeverity] = mapped_column(Enum(FindingSeverity))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pattern_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    fix_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review_run: Mapped["ReviewRun"] = relationship(back_populates="findings")
    fix_attempts: Mapped[list["FixAttempt"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )
    obsidian_notes: Mapped[list["ObsidianNote"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )


class FixAttempt(Base):
    __tablename__ = "fix_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_runs.id"), index=True
    )
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("findings.id"), index=True
    )

    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[FixStatus] = mapped_column(Enum(FixStatus), default=FixStatus.PENDING)

    original_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fixed_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_patch: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    validation_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    review_run: Mapped["ReviewRun"] = relationship(back_populates="fix_attempts")
    finding: Mapped["Finding"] = relationship(back_populates="fix_attempts")
    sandbox_results: Mapped[list["SandboxResult"]] = relationship(
        back_populates="fix_attempt", cascade="all, delete-orphan"
    )


class SandboxResult(Base):
    __tablename__ = "sandbox_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fix_attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fix_attempts.id"), index=True
    )

    language: Mapped[str] = mapped_column(String(50))
    image_used: Mapped[str] = mapped_column(String(200))
    tests_passed: Mapped[int] = mapped_column(Integer, default=0)
    tests_failed: Mapped[int] = mapped_column(Integer, default=0)
    tests_total: Mapped[int] = mapped_column(Integer, default=0)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=512)
    network_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fix_attempt: Mapped["FixAttempt"] = relationship(back_populates="sandbox_results")


class ObsidianNote(Base):
    __tablename__ = "obsidian_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("findings.id"), index=True
    )

    note_type: Mapped[str] = mapped_column(String(50))  # concept, daily, summary
    vault_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)

    wikilinks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON list

    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    finding: Mapped["Finding"] = relationship(back_populates="obsidian_notes")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    true_positives: Mapped[int] = mapped_column(Integer, default=0)
    false_positives: Mapped[int] = mapped_column(Integer, default=0)
    false_negatives: Mapped[int] = mapped_column(Integer, default=0)

    precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    case_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Engine factory ─────────────────────────────────────────────────

def get_engine(database_url: str = "sqlite:///verifyflow.db"):
    return create_engine(database_url, echo=False)


def create_tables(engine):
    Base.metadata.create_all(engine)


def get_session(engine):
    return Session(engine)
