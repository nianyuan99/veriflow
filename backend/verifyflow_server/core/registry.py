"""Agent 注册中心 — 管理审查 Agent 的注册和调度"""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .state import ReviewContext, FindingData


class ReviewAgentProtocol(Protocol):
    """审查 Agent 协议"""

    agent_type: str
    priority_levels: list[str]  # P0, P1, P2, P3

    async def review(self, context: "ReviewContext") -> list["FindingData"]:
        """执行审查，返回发现列表"""
        ...


class AgentRegistry:
    """审查 Agent 注册中心"""

    def __init__(self):
        self._agents: dict[str, ReviewAgentProtocol] = {}

    def register(self, agent: ReviewAgentProtocol):
        """注册一个审查 agent"""
        self._agents[agent.agent_type] = agent

    def unregister(self, agent_type: str):
        """移除 agent"""
        self._agents.pop(agent_type, None)

    def get(self, agent_type: str) -> ReviewAgentProtocol | None:
        """获取指定 agent"""
        return self._agents.get(agent_type)

    def list_all(self) -> list[str]:
        """列出所有已注册 agent"""
        return list(self._agents.keys())

    def get_enabled(self, enabled_types: list[str]) -> list[ReviewAgentProtocol]:
        """获取启用的 agent 列表"""
        result = []
        for t in enabled_types:
            agent = self._agents.get(t)
            if agent:
                result.append(agent)
        return result

    def clear(self):
        self._agents.clear()


# 全局注册中心单例
agent_registry = AgentRegistry()
