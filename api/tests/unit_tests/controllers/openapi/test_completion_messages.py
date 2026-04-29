from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from flask_restx import Api


def _client():
    from controllers.openapi import (
        completion_messages,  # noqa: F401
        openapi_ns,
    )

    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(openapi_ns, path="/openapi/v1")
    return app.test_client()


@patch("controllers.openapi.completion_messages.AppGenerateService")
def test_completion_returns_response_model(svc, bypass_pipeline):
    svc.generate.return_value = (
        {
            "event": "message",
            "task_id": "tk",
            "id": "m1",
            "message_id": "m1",
            "mode": "completion",
            "answer": "ok",
            "metadata": {},
            "created_at": 1700000000,
        },
        200,
    )
    fake = SimpleNamespace(mode="completion", id="app1", tenant_id="t1")
    with (
        patch("controllers.openapi.completion_messages._unpack_app", return_value=fake),
        patch("controllers.openapi.completion_messages._unpack_caller", return_value=SimpleNamespace()),
    ):
        r = _client().post(
            "/openapi/v1/apps/app1/completion-messages",
            json={"inputs": {"x": 1}, "query": "hi"},
        )
    assert r.status_code == 200
    body = r.get_json()
    assert body["answer"] == "ok"
    assert svc.generate.call_args.kwargs["invoke_from"].value == "openapi"


def test_completion_rejects_chat_mode(bypass_pipeline):
    fake = SimpleNamespace(mode="chat")
    with patch("controllers.openapi.completion_messages._unpack_app", return_value=fake):
        r = _client().post(
            "/openapi/v1/apps/app1/completion-messages",
            json={"inputs": {}, "query": "hi"},
        )
    assert r.status_code in (400, 403)
