from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import Forbidden

from controllers.openapi.auth.context import Context
from controllers.openapi.auth.steps import AppAuthzCheck
from controllers.openapi.auth.strategies import AclStrategy, MembershipStrategy
from libs.oauth_bearer import SubjectType


def _ctx(*, subject_type, account_id="acc1"):
    c = Context(request=MagicMock(), required_scope="apps:run")
    c.subject_type = subject_type
    c.subject_email = "alice@example.com"
    c.account_id = account_id
    c.app = SimpleNamespace(id="app1")
    c.tenant = SimpleNamespace(id="t1")
    return c


@patch("controllers.openapi.auth.strategies.EnterpriseService")
def test_acl_strategy_calls_inner_api(ent):
    ent.WebAppAuth.is_user_allowed_to_access_webapp.return_value = True
    assert AclStrategy().authorize(_ctx(subject_type=SubjectType.ACCOUNT)) is True
    ent.WebAppAuth.is_user_allowed_to_access_webapp.assert_called_once_with(
        user_id="alice@example.com",
        app_id="app1",
    )


@patch("controllers.openapi.auth.strategies._has_tenant_membership")
def test_membership_strategy_uses_join_lookup(member):
    member.return_value = True
    assert MembershipStrategy().authorize(_ctx(subject_type=SubjectType.ACCOUNT)) is True
    member.assert_called_once_with("acc1", "t1")


def test_membership_strategy_rejects_external_sso():
    assert MembershipStrategy().authorize(_ctx(subject_type=SubjectType.EXTERNAL_SSO, account_id=None)) is False


def test_app_authz_check_raises_when_strategy_denies():
    deny = SimpleNamespace(authorize=lambda c: False)
    with pytest.raises(Forbidden) as exc:
        AppAuthzCheck(lambda: deny)(_ctx(subject_type=SubjectType.ACCOUNT))
    assert "subject_no_app_access" in str(exc.value.description)


def test_app_authz_check_passes_when_strategy_allows():
    allow = SimpleNamespace(authorize=lambda c: True)
    AppAuthzCheck(lambda: allow)(_ctx(subject_type=SubjectType.ACCOUNT))
