"""Mutable per-request context for the openapi auth pipeline.

Every field starts None / empty and is filled in by a step. The pipeline
is the only thing that should construct or mutate Context — handlers
read populated values via the decorator's kwargs unpacking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from flask import Request

from libs.oauth_bearer import SubjectType


@dataclass
class Context:
    request: Request
    required_scope: str
    subject_type: SubjectType | None = None
    subject_email: str | None = None
    subject_issuer: str | None = None
    account_id: str | None = None
    scopes: frozenset[str] = field(default_factory=frozenset)
    token_id: str | None = None
    source: str | None = None
    expires_at: datetime | None = None
    app: object | None = None
    tenant: object | None = None
    caller: object | None = None
    caller_kind: Literal["account", "end_user"] | None = None


class Step(Protocol):
    """One responsibility. Mutate ctx or raise to short-circuit."""

    def __call__(self, ctx: Context) -> None: ...
