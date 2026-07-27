"""Obsidian Writer — 将审查发现写入 Obsidian Vault"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.state import FindingData, FixResult

VAULT_BASE = r"C:\knowledge base"
CONCEPTS_DIR = f"{VAULT_BASE}/wiki/concepts"
DAILY_DIR = f"{VAULT_BASE}/wiki/daily"


class ObsidianWriter:
    """Obsidian 知识库写入器

    写入策略：
    - 每个 Finding → 一个 concept 笔记 (frontmatter + 错误原理 + 修复原理 + wikilink)
    - 每日审查 → wiki/daily/YYYY-MM-DD.md 日报
    - 自动链接：同文件/同 pattern/同 agent 的 finding 自动建立 [[wikilink]]
    """

    def __init__(self, vault_base: str = VAULT_BASE):
        self.vault_base = vault_base
        self.concepts_dir = os.path.join(vault_base, "wiki", "concepts")
        self.daily_dir = os.path.join(vault_base, "wiki", "daily")

    async def write_concept(self, finding: "FindingData") -> dict | None:
        """为单个 Finding 写 concept 笔记"""
        try:
            os.makedirs(self.concepts_dir, exist_ok=True)

            note_id = str(uuid.uuid4())[:8]
            safe_title = self._sanitize_filename(finding.title)
            file_name = f"code-review-{finding.agent_type}-{note_id}.md"
            file_path = os.path.join(self.concepts_dir, file_name)

            content = self._build_concept_content(finding)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "finding_id": finding.id,
                "note_type": "concept",
                "vault_path": self.concepts_dir,
                "file_name": file_name,
                "title": finding.title,
                "content": content,
            }
        except Exception as e:
            print(f"Failed to write concept note: {e}")
            return None

    async def write_daily_summary(
        self,
        findings: list["FindingData"],
        fix_results: list["FixResult"],
    ) -> dict | None:
        """写每日审查摘要"""
        try:
            os.makedirs(self.daily_dir, exist_ok=True)

            today = datetime.now().strftime("%Y-%m-%d")
            file_name = f"{today}.md"
            file_path = os.path.join(self.daily_dir, file_name)

            content = self._build_daily_content(findings, fix_results, today)

            # 如果文件已存在，追加内容
            mode = "a" if os.path.exists(file_path) else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                if mode == "a":
                    f.write("\n\n---\n\n")
                f.write(content)

            return {
                "note_type": "daily",
                "vault_path": self.daily_dir,
                "file_name": file_name,
                "title": f"Code Review - {today}",
                "content": content,
            }
        except Exception as e:
            print(f"Failed to write daily summary: {e}")
            return None

    def _build_concept_content(self, f: "FindingData") -> str:
        """构建 concept 笔记内容 (含 frontmatter)"""
        tags = ["code-review", f.agent_type, f"severity-{f.severity.lower()}"]
        if f.pattern_id:
            tags.append(f.pattern_id)

        return f"""---
tags: [{", ".join(tags)}]
severity: {f.severity}
agent: {f.agent_type}
file: {f.file_path}
line: {f.line_start}
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
---

# {f.title}

## 问题描述

{f.description}

## 错误原理

该问题属于 **{f.agent_type}** 审查类别，严重度 **{f.severity}**。

**触发条件**：代码在 `[[{f.file_path}]]` 的第 {f.line_start} 行处存在以下模式：

```{self._guess_lang(f.file_path)}
{f.code_snippet if f.code_snippet else '(见原始代码)'}
```

## 修复原理

{f.suggestion if f.suggestion else '需要人工审查确定修复方案。'}

## 关联

- 文件：[[{f.file_path}]]
- Agent：{f.agent_type}
- Pattern：{f.pattern_id or 'N/A'}
"""

    def _build_daily_content(
        self,
        findings: list["FindingData"],
        fix_results: list["FixResult"],
        date: str,
    ) -> str:
        """构建每日审查摘要"""
        p0 = sum(1 for f in findings if f.severity == "P0")
        p1 = sum(1 for f in findings if f.severity == "P1")
        p2 = sum(1 for f in findings if f.severity == "P2")
        p3 = sum(1 for f in findings if f.severity == "P3")

        fixes_passed = sum(1 for r in fix_results if r.status == "sandbox_passed")
        fixes_total = len(fix_results)

        finding_list = ""
        for f in findings:
            note_ref = f"code-review-{f.agent_type}-" + str(uuid.uuid4())[:8]
            finding_list += f"- [{f.severity}] [[{note_ref}|{f.title}]] — `{f.file_path}:{f.line_start}`\n"

        return f"""## VerifyFlow 代码审查 — {date}

### 概览

| 指标 | 值 |
|------|-----|
| 发现问题总数 | {len(findings)} |
| P0 (严重) | {p0} |
| P1 (高危) | {p1} |
| P2 (中危) | {p2} |
| P3 (低危/风格) | {p3} |
| 自动修复通过 | {fixes_passed}/{fixes_total} |

### 发现列表

{finding_list}

### 修复摘要

{f'成功修复 {fixes_passed}/{fixes_total} 个问题。' if fixes_total > 0 else '本次审查未进行自动修复。'}
"""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """清理文件名中的非法字符"""
        illegal = '<>:"/\\|?*'
        for char in illegal:
            name = name.replace(char, "-")
        return name[:100]

    @staticmethod
    def _guess_lang(file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        return {
            "py": "python", "js": "javascript", "ts": "typescript",
            "go": "go", "rs": "rust", "java": "java",
        }.get(ext, "")


class ObsidianLinker:
    """自动链接引擎 — 在 finding 之间建立 [[wikilink]]"""

    def __init__(self):
        self._index: dict[str, list[str]] = {}  # key → note file names

    def build_links(self, findings: list["FindingData"]) -> dict[str, list[str]]:
        """计算每个 finding 的关联链接"""
        links: dict[str, list[str]] = {}

        # 按文件分组
        by_file: dict[str, list[str]] = {}
        for f in findings:
            if f.file_path not in by_file:
                by_file[f.file_path] = []
            by_file[f.file_path].append(f.title)

        # 同一文件的 finding 互相链接
        for f in findings:
            linked = []
            same_file = by_file.get(f.file_path, [])
            for title in same_file:
                if title != f.title:
                    linked.append(f"[[{title}]]")
            links[f.title if f.title else f.id] = linked

        return links
