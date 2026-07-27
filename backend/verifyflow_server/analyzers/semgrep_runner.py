"""Semgrep 规则引擎包装器"""

from __future__ import annotations

import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional


# Semgrep 常见安全规则配置
DEFAULT_RULES = [
    "p/sql-injection",
    "p/xss",
    "p/command-injection",
    "p/path-traversal",
    "p/secrets",
    "p/dockerfile",
    "p/python",
    "p/javascript",
    "p/golang",
    "p/java",
]


class SemgrepRunner:
    """Semgrep 工具运行器"""

    def __init__(
        self,
        semgrep_path: str = "semgrep",
        config_rules: Optional[list[str]] = None,
    ):
        self.semgrep_path = semgrep_path
        self.config_rules = config_rules or DEFAULT_RULES
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        """检查 semgrep 是否可用"""
        if self._available is None:
            try:
                result = subprocess.run(
                    [self.semgrep_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self._available = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._available = False
        return self._available

    def scan_diff(
        self,
        diff_text: str,
        target_dir: Optional[str] = None,
    ) -> list[dict]:
        """扫描 diff 涉及的代码"""
        if not self.available:
            return []

        # 将 diff 写入临时文件进行分析
        with tempfile.TemporaryDirectory() as tmpdir:
            diff_file = Path(tmpdir) / "input.diff"
            diff_file.write_text(diff_text, encoding="utf-8")

            results = self._run_semgrep(
                target=target_dir or str(tmpdir),
                config=self.config_rules,
            )

        return self._parse_results(results)

    def scan_file(self, file_path: str) -> list[dict]:
        """扫描单个文件"""
        if not self.available:
            return []

        results = self._run_semgrep(
            target=file_path,
            config=self.config_rules,
        )

        return self._parse_results(results)

    def _run_semgrep(
        self,
        target: str,
        config: list[str],
        timeout: int = 120,
    ) -> str:
        """执行 semgrep"""
        try:
            result = subprocess.run(
                [
                    self.semgrep_path,
                    "scan",
                    "--config",
                    " ".join(config),
                    "--json",
                    "--no-git-ignore",
                    "--max-target-bytes=5000000",
                    target,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    def _parse_results(self, raw: str) -> list[dict]:
        """解析 semgrep JSON 输出"""
        if not raw.strip():
            return []

        try:
            data = json.loads(raw)
            findings = []
            results = data.get("results", []) if isinstance(data, dict) else []
            for r in results:
                findings.append({
                    "check_id": r.get("check_id", ""),
                    "path": r.get("path", ""),
                    "start_line": r.get("start", {}).get("line", 0),
                    "end_line": r.get("end", {}).get("line", 0),
                    "message": r.get("extra", {}).get("message", ""),
                    "severity": r.get("extra", {}).get("severity", "WARNING"),
                })
            return findings
        except json.JSONDecodeError:
            return []
