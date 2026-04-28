"""Shared response substructures for openapi endpoints."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class MessageMetadata(BaseModel):
    usage: UsageInfo | None = None
    retriever_resources: list[dict[str, Any]] = []
