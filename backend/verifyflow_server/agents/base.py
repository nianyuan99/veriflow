"""审查 Agent 基类"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from ..core.state import FindingData

if TYPE_CHECKING:
    from ..core.state import ReviewContext


class BaseReviewAgent(ABC):
    """审查 Agent 基类"""

    agent_type: str = "base"
    priority_levels: list[str] = ["P0", "P1", "P2", "P3"]

    def __init__(self, llm_client: BaseChatModel):
        self.llm = llm_client

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        ...

    def get_user_prompt(self, context: "ReviewContext") -> str:
        """构建用户提示词"""
        files_list = "\n".join(f"  - {f}" for f in context.files_changed)
        return f"""请审查以下代码变更：

**变更文件**：
{files_list}

**变更统计**：+{context.additions} -{context.deletions} 行

**修改的函数**：{", ".join(context.functions_modified) if context.functions_modified else "未识别"}

**语言**：{context.language}

**Diff 内容**：
```diff
{context.diff_raw[:8000]}
```

请以 JSON 数组格式返回发现的问题，每个问题包含：
- title: 简短标题
- description: 详细描述
- severity: P0/P1/P2/P3
- file_path: 文件路径
- line_start: 起始行号 (可选)
- suggestion: 修复建议
- code_snippet: 相关代码片段 (可选)
- pattern_id: 缺陷模式ID (可选)

如果没有发现问题，返回空数组 `[]`。"""

    async def review(self, context: "ReviewContext") -> list["FindingData"]:
        """执行审查"""
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=self.get_user_prompt(context)),
        ]

        response = await self.llm.ainvoke(messages)
        return self._parse_response(response.content)

    def _parse_response(self, raw: str) -> list["FindingData"]:
        """解析 LLM 返回的 JSON"""
        # 尝试提取 JSON 数组
        text = raw.strip()
        # 处理 markdown code block
        if "```" in text:
            lines = text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```") and not in_json:
                    in_json = True
                    continue
                elif line.startswith("```") and in_json:
                    break
                if in_json:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        try:
            data = json.loads(text)
            if isinstance(data, list):
                findings = []
                for item in data:
                    findings.append(
                        FindingData(
                            agent_type=self.agent_type,
                            file_path=item.get("file_path", ""),
                            line_start=item.get("line_start"),
                            line_end=item.get("line_end"),
                            severity=item.get("severity", "P2"),
                            title=item.get("title", "Untitled"),
                            description=item.get("description", ""),
                            suggestion=item.get("suggestion", ""),
                            code_snippet=item.get("code_snippet", ""),
                            pattern_id=item.get("pattern_id"),
                        )
                    )
                return findings
        except (json.JSONDecodeError, TypeError):
            pass

        return []
