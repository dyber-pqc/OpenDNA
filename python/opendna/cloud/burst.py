"""Cloud burst: spin up GPU instances on vast.ai / runpod / lambda labs.

Credentials live in ~/.opendna/cloud.json (never committed) or env vars:
VAST_API_KEY, RUNPOD_API_KEY, LAMBDA_API_KEY. Current implementations are
stubs that return a structured response; the plumbing for talking to each
provider's REST API is outlined so it can be swapped in without touching
callers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

SUPPORTED = ("vast", "runpod", "lambda")

ENV_KEYS = {
    "vast": "VAST_API_KEY",
    "runpod": "RUNPOD_API_KEY",
    "lambda": "LAMBDA_API_KEY",
}

DOCKER_IMAGE = "opendna/opendna:latest"


def _config_path() -> Path:
    p = Path.home() / ".opendna"
    p.mkdir(parents=True, exist_ok=True)
    return p / "cloud.json"


def _load() -> Dict[str, Any]:
    p = _config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    p = _config_path()
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass


def register_provider(name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Store credentials for a cloud provider."""
    if name not in SUPPORTED:
        raise ValueError(f"unknown provider {name!r}; supported: {SUPPORTED}")
    data = _load()
    data[name] = dict(config)
    _save(data)
    return {"status": "ok", "provider": name}


def _api_key(name: str) -> str | None:
    env = os.environ.get(ENV_KEYS.get(name, ""), "")
    if env:
        return env
    data = _load()
    cfg = data.get(name) or {}
    return cfg.get("api_key") or cfg.get("token")


def list_providers() -> List[Dict[str, Any]]:
    data = _load()
    out = []
    for name in SUPPORTED:
        has_key = bool(_api_key(name))
        out.append({
            "name": name,
            "configured": name in data or bool(os.environ.get(ENV_KEYS[name])),
            "has_credentials": has_key,
            "env_var": ENV_KEYS[name],
            "status": "ready" if has_key else "no_credentials",
        })
    return out


def _no_credentials(provider: str) -> Dict[str, Any]:
    return {
        "status": "no_credentials",
        "provider": provider,
        "message": (
            f"No API key for {provider}. Set {ENV_KEYS[provider]} or call "
            f"register_provider({provider!r}, {{'api_key': '...'}})."
        ),
    }


def _burst_vast(params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    # Stub: would POST to https://console.vast.ai/api/v0/asks/ to search
    # offers, PUT /asks/<id>/ to rent, start docker run opendna/opendna:latest,
    # then poll /instances/ until state == 'running'.
    return {
        "status": "submitted",
        "provider": "vast",
        "image": DOCKER_IMAGE,
        "params": params,
        "note": "stub - vast.ai REST plumbing not yet wired",
    }


def _burst_runpod(params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    # Stub: would POST GraphQL mutation to https://api.runpod.io/graphql
    # creating a pod with imageName=opendna/opendna:latest.
    return {
        "status": "submitted",
        "provider": "runpod",
        "image": DOCKER_IMAGE,
        "params": params,
        "note": "stub - runpod GraphQL not yet wired",
    }


def _burst_lambda(params: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    # Stub: would POST to https://cloud.lambdalabs.com/api/v1/instance-operations/launch
    # with docker-compose user-data that runs opendna/opendna:latest.
    return {
        "status": "submitted",
        "provider": "lambda",
        "image": DOCKER_IMAGE,
        "params": params,
        "note": "stub - lambda labs REST not yet wired",
    }


_DISPATCH = {
    "vast": _burst_vast,
    "runpod": _burst_runpod,
    "lambda": _burst_lambda,
}


def burst_job(job_type: str, params: Dict[str, Any], provider: str) -> Dict[str, Any]:
    if provider not in SUPPORTED:
        return {
            "status": "error",
            "provider": provider,
            "message": f"unknown provider; supported: {SUPPORTED}",
        }
    api_key = _api_key(provider)
    if not api_key:
        return _no_credentials(provider)
    fn = _DISPATCH[provider]
    result = fn(params or {}, api_key)
    result["job_type"] = job_type
    return result
