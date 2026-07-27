"""Diff 解析器 — 将 unified diff 解析为结构化数据"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DiffHunk:
    """单个 diff hunk"""
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)


@dataclass
class DiffFile:
    """单个文件的 diff 信息"""
    old_path: str
    new_path: str
    hunks: list[DiffHunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    is_renamed: bool = False

    @property
    def additions(self) -> int:
        return sum(
            1 for h in self.hunks for l in h.lines if l.startswith("+")
        )

    @property
    def deletions(self) -> int:
        return sum(
            1 for h in self.hunks for l in h.lines if l.startswith("-")
        )


@dataclass
class ParsedDiff:
    """解析后的完整 diff"""
    files: list[DiffFile] = field(default_factory=list)
    raw: str = ""

    @property
    def files_changed(self) -> list[str]:
        return [f.new_path or f.old_path for f in self.files]

    @property
    def total_additions(self) -> int:
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(f.deletions for f in self.files)

    @property
    def language_hint(self) -> str:
        """通过文件扩展名推测语言"""
        extensions = set()
        for fp in self.files_changed:
            _, ext = fp.rsplit(".", 1) if "." in fp else (fp, "")
            extensions.add(ext)

        ext_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "go": "go",
            "rs": "rust",
            "java": "java",
            "rb": "ruby",
            "php": "php",
            "c": "c",
            "cpp": "cpp",
            "h": "c",
            "hpp": "cpp",
            "css": "css",
            "html": "html",
            "sql": "sql",
            "sh": "shell",
            "yaml": "yaml",
            "yml": "yaml",
            "json": "json",
            "md": "markdown",
        }
        if len(extensions) == 1:
            ext = next(iter(extensions)).lower()
            return ext_map.get(ext, "unknown")
        return "multi-language"


# ── 主解析函数 ────────────────────────────────────────────────────

DIFF_FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
DIFF_NEW_FILE_RE = re.compile(r"^new file mode \d+$")
DIFF_DELETED_FILE_RE = re.compile(r"^deleted file mode \d+$")
DIFF_RENAME_RE = re.compile(r"^rename (?:from|to) (.+)$")
HUNK_HEADER_RE = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@")


def parse_diff(diff_text: str) -> ParsedDiff:
    """解析 unified diff 文本"""
    parsed = ParsedDiff(raw=diff_text)
    if not diff_text.strip():
        return parsed

    lines = diff_text.split("\n")
    current_file: DiffFile | None = None
    current_hunk: DiffHunk | None = None

    for line in lines:
        # 新文件
        m = DIFF_FILE_RE.match(line)
        if m:
            if current_file:
                if current_hunk:
                    current_file.hunks.append(current_hunk)
                parsed.files.append(current_file)
            current_file = DiffFile(old_path=m.group(1), new_path=m.group(2))
            current_hunk = None
            continue

        # 新文件模式
        if DIFF_NEW_FILE_RE.match(line) and current_file:
            current_file.is_new = True
            continue
        if DIFF_DELETED_FILE_RE.match(line) and current_file:
            current_file.is_deleted = True
            continue
        if DIFF_RENAME_RE.match(line) and current_file:
            current_file.is_renamed = True
            continue

        # Hunk header
        m = HUNK_HEADER_RE.match(line)
        if m:
            if current_file and current_hunk:
                current_file.hunks.append(current_hunk)
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) else 1
            current_hunk = DiffHunk(
                header=line,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
            )
            continue

        # Hunks lines
        if current_hunk is not None:
            if line.startswith(" ") or line.startswith("+") or line.startswith("-"):
                current_hunk.lines.append(line)

    # 保存最后一个
    if current_file:
        if current_hunk:
            current_file.hunks.append(current_hunk)
        parsed.files.append(current_file)

    return parsed


def extract_functions(diff: ParsedDiff) -> list[str]:
    """从 diff 中提取可能被修改的函数名"""
    func_pattern = re.compile(
        r"^[+\-]\s*(?:async\s+)?(?:def|function|func|class)\s+(\w+)",
        re.MULTILINE,
    )
    matches = func_pattern.findall(diff.raw)
    return list(set(matches))


def verify_tree_sitter_available() -> bool:
    """检查 tree-sitter 是否可用"""
    try:
        import tree_sitter  # noqa: F401
        return True
    except ImportError:
        return False
