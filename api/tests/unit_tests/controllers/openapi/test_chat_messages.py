from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from flask_restx import Api


def _client():
    from controllers.openapi import (
        chat_messages,  # noqa: F401
        openapi_ns,
    )

    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(openapi_ns, path="/openapi/v1")
    return app.test_client()


@patch("controllers.openapi.chat_messages.AppGenerateService")
def test_chat_dispatches_and_returns_response_model(svc, bypass_pipeline):
    svc.generate.return_value = (
        {
            "event": "message",
            "task_id": "tk1",
            "id": "m1",
            "message_id": "m1",
            "conversation_id": "c1",
            "mode": "chat",
            "answer": "hi",
            "metadata": {},
            "created_at": 1700000000,
        },
        200,
    )
    fake = SimpleNamespace(mode="chat", id="app1", tenant_id="t1")
    with (
        patch("controllers.openapi.chat_messages._unpack_app", return_value=fake),
        patch("controllers.openapi.chat_messages._unpack_caller", return_value=SimpleNamespace()),
    ):
        r = _client().post("/openapi/v1/apps/app1/chat-messages", json={"query": "hi", "inputs": {}})
    assert r.status_code == 200
    body = r.get_json()
    assert body["conversation_id"] == "c1"
    assert body["answer"] == "hi"
    assert svc.generate.call_args.kwargs["invoke_from"].value == "openapi"


@patch("controllers.openapi.chat_messages.AppGenerateService")
def test_chat_strips_user_field_from_body(svc, bypass_pipeline):
    svc.generate.return_value = (
        {
            "event": "message",
            "task_id": "tk1",
            "id": "m1",
            "message_id": "m1",
            "conversation_id": "c1",
            "mode": "chat",
            "answer": "hi",
            "metadata": {},
            "created_at": 1700000000,
        },
        200,
    )
    fake = SimpleNamespace(mode="chat", id="app1", tenant_id="t1")
    with (
        patch("controllers.openapi.chat_messages._unpack_app", return_value=fake),
        patch("controllers.openapi.chat_messages._unpack_caller", return_value=SimpleNamespace()),
    ):
        _client().post(
            "/openapi/v1/apps/app1/chat-messages",
            json={"query": "hi", "inputs": {}, "user": "spoof@x.com"},
        )
    args = svc.generate.call_args.kwargs["args"]
    assert "user" not in args


def test_chat_rejects_non_chat_mode(bypass_pipeline):
    fake = SimpleNamespace(mode="completion")
    with patch("controllers.openapi.chat_messages._unpack_app", return_value=fake):
        r = _client().post("/openapi/v1/apps/app1/chat-messages", json={"query": "hi", "inputs": {}})
    assert r.status_code in (400, 403)


def test_chat_rejects_invalid_body(bypass_pipeline):
    fake = SimpleNamespace(mode="chat", id="app1", tenant_id="t1")
    with patch("controllers.openapi.chat_messages._unpack_app", return_value=fake):
        r = _client().post("/openapi/v1/apps/app1/chat-messages", json={"query": "hi"})
    assert r.status_code in (400, 422)
