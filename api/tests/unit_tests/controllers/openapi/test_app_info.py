from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from flask_restx import Api


def _client():
    from controllers.openapi import (
        app_info,  # noqa: F401
        openapi_ns,
    )

    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(openapi_ns, path="/openapi/v1")
    return app.test_client()


def test_app_info_returns_response_model(bypass_pipeline):
    app_obj = SimpleNamespace(
        id="app1",
        name="X",
        description="d",
        mode="chat",
        author_name="alice",
        tags=[SimpleNamespace(name="prod")],
    )
    with patch("controllers.openapi.app_info._unpack_app", return_value=app_obj):
        r = _client().get("/openapi/v1/apps/app1/info")
    assert r.status_code == 200
    body = r.get_json()
    assert body == {
        "id": "app1",
        "name": "X",
        "description": "d",
        "mode": "chat",
        "author_name": "alice",
        "tags": ["prod"],
    }


def test_app_info_response_model_validates():
    from controllers.openapi.app_info import AppInfoResponse

    m = AppInfoResponse(id="x", name="N", mode="chat")
    assert m.tags == []
    assert m.description is None
