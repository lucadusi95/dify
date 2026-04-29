"""APP_PIPELINE — the only auth scheme for openapi app endpoints.

Endpoints attach via @APP_PIPELINE.guard(scope=…). No alternative paths.
"""

from __future__ import annotations

from controllers.openapi.auth.pipeline import Pipeline
from controllers.openapi.auth.steps import (
    AppAuthzCheck,
    AppResolver,
    BearerCheck,
    CallerMount,
    ScopeCheck,
)
from controllers.openapi.auth.strategies import (
    AccountMounter,
    AclStrategy,
    AppAuthzStrategy,
    EndUserMounter,
    MembershipStrategy,
)
from services.feature_service import FeatureService


def _resolve_app_authz_strategy() -> AppAuthzStrategy:
    if FeatureService.get_system_features().webapp_auth.enabled:
        return AclStrategy()
    return MembershipStrategy()


APP_PIPELINE = Pipeline(
    BearerCheck(),
    ScopeCheck(),
    AppResolver(),
    AppAuthzCheck(_resolve_app_authz_strategy),
    CallerMount(AccountMounter(), EndUserMounter()),
)
