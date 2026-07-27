"""Docker 沙箱管理器 — 隔离环境中验证修复代码"""

from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SandboxConfig:
    """沙箱配置"""
    image: str = "python:3.11-slim"
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_enabled: bool = False
    timeout_seconds: int = 60
    working_dir: str = "/app"


@dataclass
class SandboxResult:
    """沙箱运行结果"""
    passed: bool = False
    output: str = ""
    exit_code: int = -1
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    duration_ms: int = 0
    error: str = ""


# ── 语言到镜像映射 ────────────────────────────────────────────────

LANGUAGE_IMAGES = {
    "python": "python:3.11-slim",
    "javascript": "node:20-slim",
    "typescript": "node:20-slim",
    "go": "golang:1.22-alpine",
    "rust": "rust:1.75-slim",
}

LANGUAGE_TEST_COMMANDS = {
    "python": ["pytest", "--tb=short", "-x"],
    "javascript": ["npx", "jest", "--verbose"],
    "typescript": ["npx", "jest", "--verbose"],
    "go": ["go", "test", "./..."],
    "rust": ["cargo", "test"],
}


class DockerSandbox:
    """Docker 沙箱生命周期管理"""

    def __init__(
        self,
        language: str = "python",
        repo_path: str = "",
        config: Optional[SandboxConfig] = None,
    ):
        self.language = language
        self.repo_path = repo_path
        self.config = config or SandboxConfig(
            image=LANGUAGE_IMAGES.get(language, "python:3.11-slim"),
        )
        self._client = None

    @property
    def client(self):
        """延迟初始化 Docker 客户端"""
        if self._client is None:
            try:
                import docker

                self._client = docker.from_env()
            except ImportError:
                raise RuntimeError(
                    "docker Python SDK not installed. "
                    "Run: pip install docker"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Docker: {e}")
        return self._client

    async def run_tests(
        self,
        diff_patch: str,
        test_command: Optional[list[str]] = None,
    ) -> SandboxResult:
        """在 Docker 容器中运行测试"""
        import asyncio

        if not diff_patch.strip():
            return SandboxResult(
                passed=True,
                output="No changes to verify",
                exit_code=0,
            )

        # 构建测试环境
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # 写入 patch
            (work_dir / "fix.patch").write_text(diff_patch, encoding="utf-8")

            # 创建测试脚本
            test_script = self._build_test_script(test_command)
            (work_dir / "run_tests.sh").write_text(test_script, encoding="utf-8")

            # 复制测试文件 (如果有)
            if self.repo_path and os.path.isdir(self.repo_path):
                self._copy_test_files(work_dir)

            try:
                container = await asyncio.to_thread(
                    self.client.containers.run,
                    self.config.image,
                    command=["/bin/bash", "/app/run_tests.sh"],
                    volumes={
                        str(work_dir.absolute()): {
                            "bind": "/app",
                            "mode": "rw",
                        },
                    },
                    mem_limit=self.config.memory_limit,
                    network_mode="none" if not self.config.network_enabled else "bridge",
                    working_dir="/app",
                    detach=True,
                    remove=True,
                )

                # 等待完成
                result = await asyncio.to_thread(
                    container.wait,
                    timeout=self.config.timeout_seconds,
                )

                logs = await asyncio.to_thread(container.logs)
                stdout = logs.decode("utf-8", errors="replace")

                exit_code = result.get("StatusCode", -1)
                passed = exit_code == 0

                # 解析测试结果
                tests_passed, tests_failed, tests_total = self._parse_test_output(
                    stdout, self.language
                )

                return SandboxResult(
                    passed=passed,
                    output=stdout,
                    exit_code=exit_code,
                    tests_passed=tests_passed,
                    tests_failed=tests_failed,
                    tests_total=tests_total,
                )

            except Exception as e:
                return SandboxResult(
                    passed=False,
                    output=str(e),
                    error=str(e),
                )

    def _build_test_script(self, test_command: Optional[list[str]] = None) -> str:
        """构建沙箱内测试脚本"""
        cmd = test_command or LANGUAGE_TEST_COMMANDS.get(
            self.language, ["pytest", "--tb=short"]
        )
        cmd_str = " ".join(cmd)

        return f"""#!/bin/bash
set -e

echo "=== VerifyFlow Sandbox ==="
echo "Language: {self.language}"
echo "Image: {self.config.image}"
echo ""

# 应用修复 patch
if [ -f /app/fix.patch ] && [ -s /app/fix.patch ]; then
    echo "Applying fix patch..."
    patch -p1 < /app/fix.patch || echo "Warning: patch apply failed, continuing..."
fi

# 安装依赖
if [ -f /app/requirements.txt ]; then
    pip install -r /app/requirements.txt -q 2>/dev/null || true
fi

if [ -f /app/package.json ]; then
    npm install --silent 2>/dev/null || true
fi

# 运行测试
echo ""
echo "Running tests: {cmd_str}"
echo "---"

{cmd_str} 2>&1
EXIT_CODE=$?

echo ""
echo "---"
echo "Exit code: $EXIT_CODE"
exit $EXIT_CODE
"""

    def _copy_test_files(self, work_dir: Path):
        """将仓库中的测试文件复制到沙箱工作目录"""
        import shutil

        # 复制测试目录
        for test_dir in ["tests", "test", "__tests__", "spec"]:
            src = Path(self.repo_path) / test_dir
            if src.exists() and src.is_dir():
                dst = work_dir / test_dir
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # 复制配置文件
        for cfg in [
            "pytest.ini", "setup.cfg", "pyproject.toml",
            "package.json", "jest.config.js", "jest.config.ts",
            "go.mod", "Cargo.toml",
        ]:
            src = Path(self.repo_path) / cfg
            if src.exists():
                shutil.copy2(src, work_dir / cfg)

    def _parse_test_output(
        self, output: str, language: str
    ) -> tuple[int, int, int]:
        """从测试输出中解析通过/失败数"""
        import re

        # Pytest 格式: X passed, Y failed
        pytest_match = re.search(
            r"(\d+)\s*passed.*?(\d+)\s*failed",
            output,
        )
        if pytest_match:
            passed = int(pytest_match.group(1))
            failed = int(pytest_match.group(2))
            return passed, failed, passed + failed

        # Jest 格式: Tests: X passed, Y failed, Z total
        jest_match = re.search(
            r"Tests:\s*(\d+)\s*passed.*?(\d+)\s*failed.*?(\d+)\s*total",
            output,
        )
        if jest_match:
            return (
                int(jest_match.group(1)),
                int(jest_match.group(2)),
                int(jest_match.group(3)),
            )

        # Go test 格式
        go_match = re.search(r"(\d+)\s*tests?\s*passed", output)
        if go_match:
            return int(go_match.group(1)), 0, int(go_match.group(1))

        return 0, 0, 0
