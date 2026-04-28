"""Pipeline steps. Each is one responsibility.

BearerCheck is the only step that touches the token registry; downstream
steps see only the populated Context.
"""
from __future__ import annotations

from typing import Callable

from werkzeug.exceptions import BadRequest, Forbidden, NotFound, Unauthorized

from controllers.openapi.auth.context import Context
from controllers.openapi.auth.strategies import AppAuthzStrategy, CallerMounter
from extensions.ext_database import db
from libs.oauth_bearer import TokenExpired, get_authenticator, sha256_hex
from models import App, Tenant, TenantStatus


def _registry():
    return get_authenticator()._registry  # noqa: SLF001


def _extract_bearer(req) -> str | None:
    auth = req.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    return auth.split(None, 1)[1].strip() or None


def _hash_token(token: str) -> str:
    return sha256_hex(token)


class BearerCheck:
    """Resolve bearer → populate identity fields."""

    def __call__(self, ctx: Context) -> None:
        token = _extract_bearer(ctx.request)
        if not token:
            raise Unauthorized("bearer required")

        kind = _registry().find(token)
        if kind is None:
            raise Unauthorized("invalid bearer prefix")

        try:
            row = kind.resolver.resolve(_hash_token(token))
        except TokenExpired:
            raise Unauthorized("token expired")
        if row is None:
            raise Unauthorized("invalid bearer")

        ctx.subject_type = kind.subject_type
        ctx.subject_email = row.subject_email
        ctx.subject_issuer = row.subject_issuer
        ctx.account_id = row.account_id
        ctx.scopes = kind.scopes
        ctx.source = kind.source
        ctx.token_id = row.token_id
        ctx.expires_at = row.expires_at


class ScopeCheck:
    """Verify ctx.scopes (already populated by BearerCheck) covers required."""

    def __call__(self, ctx: Context) -> None:
        if "full" in ctx.scopes or ctx.required_scope in ctx.scopes:
            return
        raise Forbidden("insufficient_scope")


class AppResolver:
    """Read app_id from request.view_args, populate ctx.app + ctx.tenant.

    Every endpoint using APP_PIPELINE must declare ``<string:app_id>`` in
    its route — that is the design lock-in (no body / header coupling).
    """

    def __call__(self, ctx: Context) -> None:
        app_id = (ctx.request.view_args or {}).get("app_id")
        if not app_id:
            raise BadRequest("app_id is required in path")
        app = db.session.get(App, app_id)
        if not app or app.status != "normal":
            raise NotFound("app not found")
        if not app.enable_api:
            raise Forbidden("service_api_disabled")
        tenant = db.session.get(Tenant, app.tenant_id)
        if tenant is None or tenant.status == TenantStatus.ARCHIVE:
            raise Forbidden("workspace unavailable")
        ctx.app, ctx.tenant = app, tenant


class AppAuthzCheck:
    def __init__(self, resolve_strategy: Callable[[], AppAuthzStrategy]) -> None:
        self._resolve = resolve_strategy

    def __call__(self, ctx: Context) -> None:
        if not self._resolve().authorize(ctx):
            raise Forbidden("subject_no_app_access")


class CallerMount:
    def __init__(self, *mounters: CallerMounter) -> None:
        self._mounters = mounters

    def __call__(self, ctx: Context) -> None:
        for m in self._mounters:
            if m.applies_to(ctx.subject_type):
                m.mount(ctx)
                return
        raise Unauthorized("no caller mounter for subject type")
