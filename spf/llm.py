"""Pluggable LLM. Pick with SPF_LLM = none | anthropic | openai | ollama.

"none" means no LLM at all: the RAG chain still runs and returns a template
answer built from the retrieved products, so the project works with zero keys.
"""
from __future__ import annotations

from . import config

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-5-5",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2",
}


def get_llm(provider: str | None = None, model: str | None = None):
    provider = (provider or config.LLM_PROVIDER).lower()
    model = model or config.LLM_MODEL or DEFAULT_MODELS.get(provider, "")
    if provider == "none":
        return None
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # needs ANTHROPIC_API_KEY

        return ChatAnthropic(model=model, temperature=0, max_tokens=600)
    if provider == "openai":
        from langchain_openai import ChatOpenAI  # needs OPENAI_API_KEY

        return ChatOpenAI(model=model, temperature=0)
    if provider == "ollama":
        from langchain_ollama import ChatOllama  # free, local: `ollama pull llama3.2`

        return ChatOllama(model=model, temperature=0)
    raise ValueError(f"Unknown SPF_LLM={provider!r}")
