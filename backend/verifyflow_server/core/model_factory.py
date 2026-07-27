"""LLM 模型工厂 — 支持 OpenAI / Claude / DeepSeek 切换"""

import os
from enum import Enum
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class LLMConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60


# ── 默认模型映射 ──────────────────────────────────────────────────

PROVIDER_DEFAULTS: dict[LLMProvider, dict[str, str]] = {
    LLMProvider.OPENAI: {
        "cheap": "gpt-4o-mini",
        "default": "gpt-4o",
        "smart": "gpt-4o",
    },
    LLMProvider.ANTHROPIC: {
        "cheap": "claude-haiku-4-5-20251001",
        "default": "claude-sonnet-5",
        "smart": "claude-opus-5",
    },
    LLMProvider.DEEPSEEK: {
        "cheap": "deepseek-chat",
        "default": "deepseek-chat",
        "smart": "deepseek-chat",
    },
}

PROVIDER_BASE_URLS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "https://api.openai.com/v1",
    LLMProvider.ANTHROPIC: "https://api.anthropic.com",
    LLMProvider.DEEPSEEK: "https://api.deepseek.com",
}


def resolve_api_key(provider: LLMProvider, explicit_key: Optional[str] = None) -> Optional[str]:
    """按 explicit > env var 优先级解析 API key"""
    if explicit_key:
        return explicit_key
    env_map = {
        LLMProvider.OPENAI: "OPENAI_API_KEY",
        LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
    }
    return os.environ.get(env_map[provider])


def create_llm_client(config: LLMConfig):
    """根据配置创建对应 LLM 客户端"""
    api_key = resolve_api_key(config.provider, config.api_key)
    base_url = config.base_url or PROVIDER_BASE_URLS[config.provider]

    if config.provider == LLMProvider.DEEPSEEK:
        # DeepSeek 兼容 OpenAI 接口
        return ChatOpenAI(
            model=config.model,
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )

    if config.provider == LLMProvider.OPENAI:
        return ChatOpenAI(
            model=config.model,
            api_key=api_key,
            base_url=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )

    if config.provider == LLMProvider.ANTHROPIC:
        return ChatAnthropic(
            model=config.model,
            api_key=api_key,
            base_url=base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )

    raise ValueError(f"Unsupported provider: {config.provider}")


def get_model_for_tier(provider: LLMProvider, tier: str = "default") -> str:
    """获取指定 provider 和 tier 的模型名"""
    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS[LLMProvider.OPENAI])
    return defaults.get(tier, defaults["default"])


def create_cheap_client(provider: LLMProvider = LLMProvider.OPENAI):
    """快速创建低成本模型客户端 (用于 P3 审查)"""
    config = LLMConfig(
        provider=provider,
        model=get_model_for_tier(provider, "cheap"),
        temperature=0.0,
        max_tokens=2048,
    )
    return create_llm_client(config)


def create_default_client(provider: LLMProvider = LLMProvider.OPENAI):
    """创建默认模型客户端"""
    config = LLMConfig(
        provider=provider,
        model=get_model_for_tier(provider, "default"),
    )
    return create_llm_client(config)


def create_smart_client(provider: LLMProvider = LLMProvider.OPENAI):
    """创建智能模型客户端 (用于复杂推理)"""
    config = LLMConfig(
        provider=provider,
        model=get_model_for_tier(provider, "smart"),
        temperature=0.05,
        max_tokens=8192,
    )
    return create_llm_client(config)
