"""VerifyFlow CLI — 命令行代码审查工具"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

app = typer.Typer(
    name="verifyflow",
    help="AI Code Review Agent + Sandbox Verify + Obsidian Sync",
)
console = Console()


# ── Helpers ────────────────────────────────────────────────────────


def _get_api_url() -> str:
    return os.environ.get("VERIFYFLOW_API_URL", "http://localhost:8710")


def _read_diff(path: str) -> str:
    """读取 diff 文件"""
    diff_path = Path(path)
    if diff_path.exists():
        return diff_path.read_text(encoding="utf-8")
    return path  # 直接作为 diff 文本


async def _call_api(method: str, endpoint: str, data: dict | None = None):
    """调用后端 API"""
    import httpx

    url = f"{_get_api_url()}{endpoint}"
    async with httpx.AsyncClient(timeout=300) as client:
        if method == "GET":
            resp = await client.get(url)
        elif method == "POST":
            resp = await client.post(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        resp.raise_for_status()
        return resp.json()


# ── Commands ───────────────────────────────────────────────────────


@app.command()
def review(
    diff: str = typer.Option(
        ..., "--diff", "-d", help="Diff 文件路径或 diff 文本"
    ),
    repo: str = typer.Option(
        "", "--repo", "-r", help="仓库路径"
    ),
    provider: str = typer.Option(
        "openai", "--provider", "-p", help="LLM 提供商 (openai/anthropic/deepseek)"
    ),
    model: str = typer.Option(
        "", "--model", "-m", help="LLM 模型名"
    ),
    agents: Optional[str] = typer.Option(
        None, "--agents", "-a", help="启用的 agent (逗号分隔), 默认全部"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="输出 JSON 结果到文件"
    ),
):
    """对代码 diff 运行 AI 审查"""
    diff_content = _read_diff(diff)
    enabled = agents.split(",") if agents else None

    console.print(Panel.fit(
        "[bold cyan]VerifyFlow[/bold cyan] — AI Code Review Agent",
        border_style="cyan",
    ))
    console.print(f"[dim]Provider: {provider} | Diff size: {len(diff_content)} chars[/dim]\n")

    import asyncio

    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running review...", total=None)

            result = await _call_api("POST", "/api/v1/review", {
                "diff_content": diff_content,
                "repo_path": repo,
                "llm_provider": provider,
                "llm_model": model,
                "enabled_agents": enabled,
            })

            progress.update(task, completed=True)
            return result

    try:
        result = asyncio.run(_run())
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

    # 显示结果
    _print_review_result(result)

    if output:
        Path(output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
        console.print(f"\n[green]Results saved to: {output}[/green]")


def _print_review_result(result: dict):
    """格式化打印审查结果"""
    # 摘要表格
    table = Table(title="审查摘要", border_style="cyan")
    table.add_column("指标", style="dim")
    table.add_column("值", style="bold")
    table.add_row("Run ID", result.get("run_id", "N/A"))
    table.add_row("Status", result.get("status", "N/A"))
    table.add_row("Total Findings", str(result.get("total_findings", 0)))
    table.add_row("P0 (Critical)", f"[red]{result.get('p0_count', 0)}[/red]")
    table.add_row("P1 (High)", f"[yellow]{result.get('p1_count', 0)}[/yellow]")
    table.add_row("P2 (Medium)", f"[blue]{result.get('p2_count', 0)}[/blue]")
    table.add_row("P3 (Low)", f"[dim]{result.get('p3_count', 0)}[/dim]")
    console.print(table)

    # 发现列表
    findings = result.get("findings", [])
    if findings:
        console.print("\n[bold]Findings:[/bold]")
        for f in findings:
            color = {
                "P0": "red",
                "P1": "yellow",
                "P2": "blue",
                "P3": "dim",
            }.get(f.get("severity", "P2"), "white")

            console.print(
                f"  [{color}]● {f['severity']}[/{color}] "
                f"[bold]{f['title']}[/bold] — "
                f"[dim]{f.get('agent_type', 'unknown')}[/dim] "
                f"[dim]{f.get('file_path', '')}:{f.get('line_start', '')}[/dim]"
            )


@app.command()
def fix(
    finding_id: str = typer.Option(
        ..., "--finding", "-f", help="Finding ID to fix"
    ),
    auto_verify: bool = typer.Option(
        True, "--verify/--no-verify", help="Auto verify in sandbox"
    ),
):
    """为单个 finding 生成修复"""
    console.print(f"[cyan]Generating fix for finding: {finding_id}[/cyan]")

    import asyncio

    async def _run():
        return await _call_api("POST", "/api/v1/fix", {
            "finding_id": finding_id,
            "auto_verify": auto_verify,
        })

    try:
        result = asyncio.run(_run())
        console.print(f"[green]Fix attempt created: {result.get('id', 'N/A')}[/green]")
        console.print(f"Status: {result.get('status', 'N/A')}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def verify(
    fix_attempt_id: str = typer.Option(
        ..., "--fix-attempt", "-f", help="Fix attempt ID to verify"
    ),
):
    """在 Docker 沙箱中验证修复"""
    console.print(f"[cyan]Verifying fix: {fix_attempt_id}[/cyan]")

    import asyncio

    async def _run():
        return await _call_api("POST", "/api/v1/sandbox/run", {
            "fix_attempt_id": fix_attempt_id,
        })

    try:
        result = asyncio.run(_run())
        passed = result.get("passed", False)
        if passed:
            console.print(f"[green]✓ Verification passed![/green]")
        else:
            console.print(f"[red]✗ Verification failed[/red]")
        console.print(result.get("output", ""))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def bench(
    name: str = typer.Option(
        "default", "--name", "-n", help="Benchmark name"
    ),
    model: str = typer.Option(
        "", "--model", "-m", help="LLM model to benchmark"
    ),
):
    """运行 benchmark 评估审查质量"""
    console.print(Panel.fit(
        "[bold yellow]Benchmark Mode[/bold yellow] — Measuring review quality",
        border_style="yellow",
    ))

    import asyncio

    async def _run():
        return await _call_api("POST", "/api/v1/bench/run", {
            "name": name,
            "llm_model": model,
        })

    try:
        result = asyncio.run(_run())

        table = Table(title="Benchmark Results", border_style="yellow")
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold")
        table.add_row("Precision", f"{result.get('avg_precision', 0):.2%}")
        table.add_row("Recall", f"{result.get('avg_recall', 0):.2%}")
        table.add_row("F1 Score", f"[bold]{result.get('avg_f1', 0):.2%}[/bold]")
        table.add_row("True Positives", str(result.get("total_tp", 0)))
        table.add_row("False Positives", str(result.get("total_fp", 0)))
        table.add_row("False Negatives", str(result.get("total_fn", 0)))
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def config(
    provider: str = typer.Option(
        "", "--provider", "-p", help="Set default LLM provider"
    ),
    model: str = typer.Option(
        "", "--model", "-m", help="Set default model"
    ),
    show: bool = typer.Option(
        False, "--show", "-s", help="Show current config"
    ),
):
    """查看或修改配置"""
    config_path = Path.home() / ".verifyflow" / "config.json"

    if show:
        if config_path.exists():
            data = json.loads(config_path.read_text())
            console.print_json(json.dumps(data, indent=2))
        else:
            console.print("[dim]No config found. Using defaults.[/dim]")
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if config_path.exists():
        current = json.loads(config_path.read_text())

    if provider:
        current["provider"] = provider
    if model:
        current["model"] = model

    config_path.write_text(json.dumps(current, indent=2))
    console.print("[green]Config updated[/green]")


@app.command()
def sync(
    run_id: str = typer.Option(
        ..., "--run", "-r", help="Review run ID to sync"
    ),
):
    """同步审查结果到 Obsidian"""
    console.print(f"[cyan]Syncing review {run_id} to Obsidian...[/cyan]")

    import asyncio

    async def _run():
        return await _call_api("POST", "/api/v1/obsidian/sync", {
            "review_run_id": run_id,
        })

    try:
        result = asyncio.run(_run())
        console.print(
            f"[green]✓ Synced {result.get('notes_created', 0)} notes to Obsidian[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()
