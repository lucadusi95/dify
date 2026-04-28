from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from flask_restx import Api


def _client():
    from controllers.openapi import openapi_ns
    from controllers.openapi import workflow_run  # noqa: F401

    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(openapi_ns, path="/openapi/v1")
    return app.test_client()


@patch("controllers.openapi.workflow_run.AppGenerateService")
def test_workflow_run_returns_response_model(svc, bypass_pipeline):
    svc.generate.return_value = (
        {
            "workflow_run_id": "wr1",
            "task_id": "tk",
            "data": {
                "id": "wr1",
                "workflow_id": "wf1",
                "status": "succeeded",
                "outputs": {"result": "ok"},
                "elapsed_time": 1.0,
            },
        },
        200,
    )
    fake = SimpleNamespace(mode="workflow", id="app1", tenant_id="t1")
    with patch("controllers.openapi.workflow_run._unpack_app", return_value=fake), patch(
        "controllers.openapi.workflow_run._unpack_caller", return_value=SimpleNamespace()
    ):
        r = _client().post("/openapi/v1/apps/app1/workflows/run", json={"inputs": {"x": 1}})
    assert r.status_code == 200
    body = r.get_json()
    assert body["workflow_run_id"] == "wr1"
    assert body["data"]["status"] == "succeeded"
    assert svc.generate.call_args.kwargs["invoke_from"].value == "openapi"


def test_workflow_run_rejects_non_workflow(bypass_pipeline):
    fake = SimpleNamespace(mode="chat")
    with patch("controllers.openapi.workflow_run._unpack_app", return_value=fake):
        r = _client().post("/openapi/v1/apps/app1/workflows/run", json={"inputs": {}})
    assert r.status_code in (400, 403)
