
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    provider: str
    api_key: str
    model: str
    max_output_tokens: int
    timeout: int


def get_ai_config() -> AIConfig:
    return AIConfig(
        enabled=getattr(settings, "AI_ENABLED", False),
        provider=getattr(settings, "AI_PROVIDER", "openai"),
        api_key=getattr(settings, "OPENAI_API_KEY", ""),
        model=getattr(settings, "OPENAI_MODEL", "gpt-5.5"),
        max_output_tokens=getattr(
            settings,
            "AI_MAX_OUTPUT_TOKENS",
            2000,
        ),
        timeout=getattr(settings, "AI_TIMEOUT", 60),
    )


def validate_ai_config() -> AIConfig:
    config = get_ai_config()

    if not config.enabled:
        raise RuntimeError(
            "AI integration is disabled. "
            "Set AI_ENABLED=True in your environment."
        )

    if config.provider != "openai":
        raise RuntimeError(
            f"Unsupported AI provider: {config.provider}"
        )

    if not config.api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    if not config.model:
        raise RuntimeError(
            "OPENAI_MODEL is not configured."
        )

    return config
