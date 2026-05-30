"""LLM adapters (Ollama/OpenAI behind one gateway). Not on the decision hot path.

The gateway module is light at import time - the HTTP/OpenAI clients load lazily
- so importing it stays zero-infra (ADR-010). See ADR-014 for why direct provider
clients sit behind the protocol instead of LiteLLM (the documented swap).
"""

from __future__ import annotations

from contextguard.llm.gateway import (
    CloudGateway,
    Completion,
    LLMGateway,
    Message,
    OllamaGateway,
    get_gateway,
)

__all__ = [
    "CloudGateway",
    "Completion",
    "LLMGateway",
    "Message",
    "OllamaGateway",
    "get_gateway",
]
