from unittest.mock import patch

from controllers.openapi.auth.composition import APP_PIPELINE, _resolve_app_authz_strategy
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
    EndUserMounter,
    MembershipStrategy,
)


def test_app_pipeline_is_composed():
    assert isinstance(APP_PIPELINE, Pipeline)


def test_app_pipeline_step_order():
    steps = APP_PIPELINE._steps
    assert isinstance(steps[0], BearerCheck)
    assert isinstance(steps[1], ScopeCheck)
    assert isinstance(steps[2], AppResolver)
    assert isinstance(steps[3], AppAuthzCheck)
    assert isinstance(steps[4], CallerMount)


def test_caller_mount_has_both_mounters():
    cm = APP_PIPELINE._steps[4]
    kinds = {type(m) for m in cm._mounters}
    assert AccountMounter in kinds
    assert EndUserMounter in kinds


@patch("controllers.openapi.auth.composition.FeatureService")
def test_strategy_resolver_picks_acl_when_enabled(fs):
    fs.get_system_features.return_value.webapp_auth.enabled = True
    assert isinstance(_resolve_app_authz_strategy(), AclStrategy)


@patch("controllers.openapi.auth.composition.FeatureService")
def test_strategy_resolver_picks_membership_when_disabled(fs):
    fs.get_system_features.return_value.webapp_auth.enabled = False
    assert isinstance(_resolve_app_authz_strategy(), MembershipStrategy)
