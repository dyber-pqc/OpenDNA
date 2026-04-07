"""Unified LLM interface supporting multiple providers.

Auto-detects available providers in order of preference:
1. Ollama (local, free, private)
2. Anthropic API (if ANTHROPIC_API_KEY set)
3. OpenAI API (if OPENAI_API_KEY set)
4. Heuristic fallback (no real LLM)

Provides a single `chat()` function that works regardless of backend.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tool_calls: list[dict]
    raw: dict


# Models known to support tool/function calling in Ollama
TOOL_CALLING_MODELS = {
    "llama3.2", "llama3.1", "llama3.3",
    "qwen2.5", "qwen3",
    "mistral-nemo", "mistral-small",
    "firefunction", "command-r",
    "hermes3",
}


def supports_tool_calling(model_name: str) -> bool:
    """Check if an Ollama model supports tool/function calling."""
    name = model_name.lower()
    return any(family in name for family in TOOL_CALLING_MODELS)


@dataclass
class LLMProvider:
    name: str
    available: bool
    model: str
    config: dict
    supports_tools: bool = True


def detect_providers() -> list[LLMProvider]:
    """Detect which LLM providers are available."""
    providers = []

    # Ollama (local)
    try:
        with httpx.Client(timeout=2.0) as client:
            r = client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                data = r.json()
                models = [m["name"] for m in data.get("models", [])]
                # Prefer tool-calling models first
                preferred_model = None
                for candidate in ["llama3.2:3b", "llama3.2:1b", "llama3.1:8b", "qwen2.5:7b", "qwen2.5:3b"]:
                    matching = [m for m in models if candidate in m]
                    if matching:
                        preferred_model = matching[0]
                        break
                # Otherwise pick any tool-capable model
                if not preferred_model:
                    for m in models:
                        if supports_tool_calling(m):
                            preferred_model = m
                            break
                # Last resort: any model (works for plain chat, no tools)
                if not preferred_model and models:
                    preferred_model = models[0]
                if preferred_model:
                    providers.append(LLMProvider(
                        name="ollama",
                        available=True,
                        model=preferred_model,
                        config={"url": "http://localhost:11434"},
                        supports_tools=supports_tool_calling(preferred_model),
                    ))
    except Exception:
        pass

    # Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(LLMProvider(
            name="anthropic",
            available=True,
            model="claude-3-5-haiku-20241022",
            config={"api_key": os.environ["ANTHROPIC_API_KEY"]},
        ))

    # OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(LLMProvider(
            name="openai",
            available=True,
            model="gpt-4o-mini",
            config={"api_key": os.environ["OPENAI_API_KEY"]},
        ))

    # Always have a fallback
    providers.append(LLMProvider(
        name="heuristic",
        available=True,
        model="rule-based",
        config={},
    ))

    return providers


def chat(
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    system: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    preferred_provider: Optional[str] = None,
) -> LLMResponse:
    """Send a chat completion request to the best available LLM.

    Args:
        messages: list of {"role": "user"|"assistant"|"system", "content": str}
        tools: optional list of tool definitions for function calling
        system: optional system prompt
        temperature: 0.0-1.0
        max_tokens: max output tokens
        preferred_provider: force a specific provider name

    Returns:
        LLMResponse with text and any tool calls.
    """
    providers = detect_providers()
    if preferred_provider:
        providers = [p for p in providers if p.name == preferred_provider] + providers

    for provider in providers:
        try:
            if provider.name == "ollama":
                return _ollama_chat(provider, messages, tools, system, temperature, max_tokens)
            elif provider.name == "anthropic":
                return _anthropic_chat(provider, messages, tools, system, temperature, max_tokens)
            elif provider.name == "openai":
                return _openai_chat(provider, messages, tools, system, temperature, max_tokens)
            elif provider.name == "heuristic":
                return _heuristic_chat(messages, tools)
        except Exception as e:
            logger.warning(f"Provider {provider.name} failed: {e}, trying next")
            continue

    return LLMResponse(
        text="No LLM provider available.",
        provider="none",
        model="none",
        tool_calls=[],
        raw={},
    )


def _ollama_chat(provider, messages, tools, system, temperature, max_tokens):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    payload = {
        "model": provider.model,
        "messages": msgs,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    # Only pass tools if the model supports it
    if tools and provider.supports_tools:
        payload["tools"] = tools

    with httpx.Client(timeout=180.0) as client:
        r = client.post(f"{provider.config['url']}/api/chat", json=payload)
        if r.status_code != 200:
            error_text = r.text[:300]
            # If the error is about tool support, retry without tools
            if "tool" in error_text.lower() and tools:
                logger.info(f"Model {provider.model} doesn't support tools, retrying without")
                payload.pop("tools", None)
                r = client.post(f"{provider.config['url']}/api/chat", json=payload)
                if r.status_code != 200:
                    raise Exception(f"Ollama returned {r.status_code}: {r.text[:200]}")
            else:
                raise Exception(f"Ollama returned {r.status_code}: {error_text}")
        data = r.json()

    msg = data.get("message", {})
    content = msg.get("content", "")
    tool_calls = []
    for tc in msg.get("tool_calls", []) or []:
        fn = tc.get("function", {})
        tool_calls.append({
            "name": fn.get("name", ""),
            "arguments": fn.get("arguments", {}),
        })

    return LLMResponse(
        text=content,
        provider="ollama",
        model=provider.model,
        tool_calls=tool_calls,
        raw=data,
    )


def _anthropic_chat(provider, messages, tools, system, temperature, max_tokens):
    headers = {
        "x-api-key": provider.config["api_key"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": provider.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        payload["system"] = system
    if tools:
        # Convert OpenAI-style tools to Anthropic format
        payload["tools"] = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in tools
        ]

    with httpx.Client(timeout=120.0) as client:
        r = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        if r.status_code != 200:
            raise Exception(f"Anthropic returned {r.status_code}: {r.text[:200]}")
        data = r.json()

    text = ""
    tool_calls = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "name": block.get("name", ""),
                "arguments": block.get("input", {}),
            })

    return LLMResponse(
        text=text,
        provider="anthropic",
        model=provider.model,
        tool_calls=tool_calls,
        raw=data,
    )


def _openai_chat(provider, messages, tools, system, temperature, max_tokens):
    headers = {
        "Authorization": f"Bearer {provider.config['api_key']}",
        "content-type": "application/json",
    }
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    payload = {
        "model": provider.model,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=120.0) as client:
        r = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        if r.status_code != 200:
            raise Exception(f"OpenAI returned {r.status_code}: {r.text[:200]}")
        data = r.json()

    choice = data["choices"][0]["message"]
    text = choice.get("content", "") or ""
    tool_calls = []
    for tc in choice.get("tool_calls", []) or []:
        fn = tc.get("function", {})
        try:
            args = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        tool_calls.append({
            "name": fn.get("name", ""),
            "arguments": args,
        })

    return LLMResponse(
        text=text,
        provider="openai",
        model=provider.model,
        tool_calls=tool_calls,
        raw=data,
    )


def _heuristic_chat(messages, tools):
    """Last-resort: parse the user message with regex."""
    from opendna.engines.nlu import parse_intent
    user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_msg = m.get("content", "")
            break
    intent = parse_intent(user_msg)
    return LLMResponse(
        text=intent.response,
        provider="heuristic",
        model="rule-based",
        tool_calls=[],
        raw={"intent": intent.action},
    )
