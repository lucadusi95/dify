"""GET /openapi/v1/apps/<app_id>/info — port of service_api/app/app.py:AppInfoApi."""

from __future__ import annotations

from flask_restx import Resource
from pydantic import BaseModel

from controllers.openapi import openapi_ns
from controllers.openapi.auth.composition import APP_PIPELINE


class AppInfoResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    mode: str
    author_name: str | None = None
    tags: list[str] = []


def _unpack_app(app_model):
    return app_model


@openapi_ns.route("/apps/<string:app_id>/info")
class AppInfoApi(Resource):
    @APP_PIPELINE.guard(scope="apps:run")
    def get(self, app_id, app_model, caller, caller_kind):
        app = _unpack_app(app_model)
        return AppInfoResponse(
            id=app.id,
            name=app.name,
            description=app.description,
            mode=app.mode,
            author_name=app.author_name,
            tags=[t.name for t in app.tags],
        ).model_dump(mode="json")
