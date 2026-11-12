from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..config import Settings, settings
from .anthropic_provider import AnthropicProvider, VertexClaudeProvider
from .base import ModelProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


PROVIDER_LABELS = {
    "openai": "OpenAI API",
    "anthropic": "Claude API",
    "gemini": "Gemini API",
    "vertex_gemini": "Gemini on Vertex AI",
    "vertex_claude": "Claude on Vertex AI Model Garden",
}


def _adc_status() -> tuple[bool, str]:
    explicit = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if explicit:
        file = Path(explicit).expanduser()
        return (file.is_file(), "GOOGLE_APPLICATION_CREDENTIALS file found" if file.is_file() else "GOOGLE_APPLICATION_CREDENTIALS points to a missing file")
    home = Path.home()
    candidates = [home / ".config" / "gcloud" / "application_default_credentials.json"]
    app_data = os.getenv("APPDATA")
    if app_data:
        candidates.append(Path(app_data) / "gcloud" / "application_default_credentials.json")
    if any(path.is_file() for path in candidates):
        return True, "Local Application Default Credentials file found"
    if os.getenv("K_SERVICE") or os.getenv("GCE_METADATA_HOST") or os.getenv("CLOUD_SHELL"):
        return True, "Google managed environment detected; test model access to verify credentials"
    return False, "No local ADC file detected. Run scripts/gcp_local_auth.sh; managed environments can still be tested."


def provider_statuses(config: Settings = settings) -> list[dict[str, Any]]:
    adc_ok, adc_detail = _adc_status()
    project_ok = bool(config.google_cloud_project)
    return [
        {
            "id": "openai",
            "label": PROVIDER_LABELS["openai"],
            "configured": bool(config.openai_api_key),
            "default_model": config.openai_model,
            "detail": "API key configured" if config.openai_api_key else "OPENAI_API_KEY is missing",
        },
        {
            "id": "anthropic",
            "label": PROVIDER_LABELS["anthropic"],
            "configured": bool(config.anthropic_api_key),
            "default_model": config.anthropic_model,
            "detail": "API key configured" if config.anthropic_api_key else "ANTHROPIC_API_KEY is missing",
        },
        {
            "id": "gemini",
            "label": PROVIDER_LABELS["gemini"],
            "configured": bool(config.gemini_api_key),
            "default_model": config.gemini_model,
            "detail": "API key configured" if config.gemini_api_key else "GEMINI_API_KEY is missing",
        },
        {
            "id": "vertex_gemini",
            "label": PROVIDER_LABELS["vertex_gemini"],
            "configured": project_ok,
            "default_model": config.vertex_gemini_model,
            "detail": adc_detail if project_ok else "GOOGLE_CLOUD_PROJECT is missing",
            "credentials_detected": adc_ok,
            "location": config.vertex_location,
        },
        {
            "id": "vertex_claude",
            "label": PROVIDER_LABELS["vertex_claude"],
            "configured": project_ok,
            "default_model": config.vertex_claude_model,
            "detail": adc_detail if project_ok else "GOOGLE_CLOUD_PROJECT is missing",
            "credentials_detected": adc_ok,
            "location": config.vertex_claude_location,
        },
    ]


def create_provider(provider_id: str, model: str | None = None, config: Settings = settings) -> ModelProvider:
    chosen = model.strip() if model and model.strip() else None
    if provider_id == "openai":
        if not config.openai_api_key:
            raise ValueError("OpenAI is not configured. Add OPENAI_API_KEY to .env.")
        return OpenAIProvider(config.openai_api_key, chosen or config.openai_model, config.max_output_tokens)
    if provider_id == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("Claude API is not configured. Add ANTHROPIC_API_KEY to .env.")
        return AnthropicProvider(config.anthropic_api_key, chosen or config.anthropic_model, config.max_output_tokens)
    if provider_id == "gemini":
        if not config.gemini_api_key:
            raise ValueError("Gemini API is not configured. Add GEMINI_API_KEY to .env.")
        return GeminiProvider(
            api_key=config.gemini_api_key,
            model=chosen or config.gemini_model,
            max_output_tokens=config.max_output_tokens,
        )
    if provider_id == "vertex_gemini":
        if not config.google_cloud_project:
            raise ValueError("Vertex AI needs GOOGLE_CLOUD_PROJECT in .env.")
        return GeminiProvider(
            project=config.google_cloud_project,
            location=config.vertex_location,
            model=chosen or config.vertex_gemini_model,
            max_output_tokens=config.max_output_tokens,
        )
    if provider_id == "vertex_claude":
        if not config.google_cloud_project:
            raise ValueError("Vertex AI needs GOOGLE_CLOUD_PROJECT in .env.")
        return VertexClaudeProvider(
            config.google_cloud_project,
            config.vertex_claude_location,
            chosen or config.vertex_claude_model,
            config.max_output_tokens,
        )
    raise ValueError(f"Unknown provider: {provider_id}")

