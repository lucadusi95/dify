"""Audit emission for openapi app-run endpoints.

Pattern: logger.info with extra={"audit": True, "event": "app.run.openapi", ...}
matches the existing oauth_device convention. The EE OTel exporter consults
its own allowlist to decide whether to ship the line.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

EVENT_APP_RUN_OPENAPI = "app.run.openapi"


def emit_app_run(*, app_id: str, tenant_id: str, caller_kind: str, mode: str) -> None:
    logger.info(
        "audit: %s app_id=%s tenant_id=%s caller_kind=%s mode=%s",
        EVENT_APP_RUN_OPENAPI,
        app_id,
        tenant_id,
        caller_kind,
        mode,
        extra={
            "audit": True,
            "event": EVENT_APP_RUN_OPENAPI,
            "app_id": app_id,
            "tenant_id": tenant_id,
            "caller_kind": caller_kind,
            "mode": mode,
        },
    )
