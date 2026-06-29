"""Factory function for creating LLM adapters.

Reads configuration and returns the appropriate adapter instance
based on the LLM_PROVIDER setting.

Priority: environment variables > app.config.settings > defaults
"""

import os
from typing import Any

from agent.llm.base import BaseLLMAdapter


def _resolve_provider() -> tuple[str, str]:
    """Resolve LLM provider and API key from env or settings.

    Returns:
        Tuple of (provider_name, api_key)
    """
    # 1. Explicit env var takes priority (enables testing & overrides)
    env_provider = os.environ.get("LLM_PROVIDER")
    if env_provider:
        api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        return env_provider.lower(), api_key

    # 2. Try app.config.settings
    try:
        from app.config import settings
        provider = settings.llm_provider.lower()
        if provider:
            return provider, settings.dashscope_api_key
    except ImportError:
        pass

    # 3. Default fallback
    return "dashscope", os.environ.get("DASHSCOPE_API_KEY", "")


def get_llm_adapter() -> BaseLLMAdapter:
    """Create and return an LLM adapter based on configuration.

    Reads LLM_PROVIDER from environment or app.config.settings.
    Supported providers:
        - "dashscope" / "tongyi": TongyiAdapter (通义千问)
        - "openai": OpenAIAdapter
        - "ollama": OllamaAdapter

    Returns:
        Configured LLM adapter instance

    Raises:
        ValueError: If the provider is not recognized
    """
    provider, api_key = _resolve_provider()

    if provider in ("dashscope", "tongyi"):
        from agent.llm.tongyi import TongyiAdapter
        return TongyiAdapter(api_key=api_key)

    elif provider == "openai":
        from agent.llm.openai_adapter import OpenAIAdapter
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL")
        return OpenAIAdapter(api_key=openai_key, base_url=base_url)

    elif provider == "ollama":
        from agent.llm.ollama import OllamaAdapter
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaAdapter(model=model, base_url=base_url)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
