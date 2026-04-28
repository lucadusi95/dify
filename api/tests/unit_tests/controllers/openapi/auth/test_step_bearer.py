import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import Unauthorized

from controllers.openapi.auth.context import Context
from controllers.openapi.auth.steps import BearerCheck
from libs.oauth_bearer import ResolvedRow, SubjectType


def _ctx(headers):
    req = MagicMock()
    req.headers = headers
    return Context(request=req, required_scope="apps:run")


def test_bearer_check_rejects_missing_header():
    with pytest.raises(Unauthorized):
        BearerCheck()(_ctx({}))


@patch("controllers.openapi.auth.steps._registry")
def test_bearer_check_rejects_unknown_prefix(reg):
    reg.return_value.find.return_value = None
    with pytest.raises(Unauthorized):
        BearerCheck()(_ctx({"Authorization": "Bearer xxx_abc"}))


@patch("controllers.openapi.auth.steps._registry")
def test_bearer_check_populates_context(reg):
    tok_id = uuid.uuid4()
    fake_resolver = MagicMock()
    fake_resolver.resolve.return_value = ResolvedRow(
        subject_email="a@x.com",
        subject_issuer=None,
        account_id=None,
        token_id=tok_id,
        expires_at=datetime.now(UTC),
    )
    fake_kind = SimpleNamespace(
        subject_type=SubjectType.ACCOUNT,
        scopes=frozenset({"full"}),
        source="oauth-account",
        resolver=fake_resolver,
    )
    reg.return_value.find.return_value = fake_kind

    ctx = _ctx({"Authorization": "Bearer dfoa_abc"})
    BearerCheck()(ctx)

    assert ctx.subject_type == SubjectType.ACCOUNT
    assert ctx.subject_email == "a@x.com"
    assert ctx.scopes == frozenset({"full"})
    assert ctx.source == "oauth-account"
    assert ctx.token_id == tok_id
