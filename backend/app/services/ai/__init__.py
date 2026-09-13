from typing import Any


def __getattr__(name: str) -> Any:
    if name == "DeterministicDemoProcessor":
        from app.services.ai.demo_processor import DeterministicDemoProcessor
        return DeterministicDemoProcessor
    if name in ("ai_service", "AIService"):
        from app.services.ai.service import AIService, ai_service
        if name == "ai_service":
            return ai_service
        return AIService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["ai_service", "AIService", "DeterministicDemoProcessor"]
