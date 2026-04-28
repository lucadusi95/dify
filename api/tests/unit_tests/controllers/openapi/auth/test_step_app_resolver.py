from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from controllers.openapi.auth.context import Context
from controllers.openapi.auth.steps import AppResolver
from models import TenantStatus


def _ctx(view_args):
    req = MagicMock()
    req.view_args = view_args
    return Context(request=req, required_scope="apps:run")


def _app(*, status="normal", enable_api=True):
    return SimpleNamespace(id="app1", tenant_id="t1", status=status, enable_api=enable_api)


def _tenant(*, status=TenantStatus.NORMAL):
    return SimpleNamespace(id="t1", status=status)


def test_resolver_rejects_missing_path_param():
    with pytest.raises(BadRequest):
        AppResolver()(_ctx({}))


def test_resolver_rejects_none_view_args():
    with pytest.raises(BadRequest):
        AppResolver()(_ctx(None))


@patch("controllers.openapi.auth.steps.db")
def test_resolver_404_when_app_missing(db):
    db.session.get.side_effect = [None]
    with pytest.raises(NotFound):
        AppResolver()(_ctx({"app_id": "x"}))


@patch("controllers.openapi.auth.steps.db")
def test_resolver_403_when_disabled(db):
    db.session.get.side_effect = [_app(enable_api=False)]
    with pytest.raises(Forbidden) as exc:
        AppResolver()(_ctx({"app_id": "x"}))
    assert "service_api_disabled" in str(exc.value.description)


@patch("controllers.openapi.auth.steps.db")
def test_resolver_403_when_tenant_archived(db):
    db.session.get.side_effect = [_app(), _tenant(status=TenantStatus.ARCHIVE)]
    with pytest.raises(Forbidden):
        AppResolver()(_ctx({"app_id": "x"}))


@patch("controllers.openapi.auth.steps.db")
def test_resolver_populates_app_and_tenant(db):
    db.session.get.side_effect = [_app(), _tenant()]
    ctx = _ctx({"app_id": "x"})
    AppResolver()(ctx)
    assert ctx.app.id == "app1"
    assert ctx.tenant.id == "t1"
