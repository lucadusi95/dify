"""POST /openapi/v1/apps/<app_id>/completion-messages — port of
service_api/app/completion.py:CompletionApi."""
from __future__ import annotations

import logging
from typing import Any, Literal

from flask import request
from flask_restx import Resource
from pydantic import BaseModel, Field, ValidationError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

import services
from controllers.openapi import openapi_ns
from controllers.openapi._audit import emit_app_run
from controllers.openapi._models import MessageMetadata
from controllers.openapi.auth.composition import APP_PIPELINE
from controllers.service_api.app.error import (
    AppUnavailableError,
    CompletionRequestError,
    ConversationCompletedError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from core.app.entities.app_invoke_entities import InvokeFrom
from core.errors.error import (
    ModelCurrentlyNotSupportError,
    ProviderTokenNotInitError,
    QuotaExceededError,
)
from graphon.model_runtime.errors.invoke import InvokeError
from libs import helper
from models.model import App, AppMode
from services.app_generate_service import AppGenerateService

logger = logging.getLogger(__name__)


class CompletionMessageRequest(BaseModel):
    inputs: dict[str, Any]
    query: str = Field(default="")
    files: list[dict[str, Any]] | None = None
    response_mode: Literal["blocking", "streaming"] | None = None


class CompletionMessageResponse(BaseModel):
    event: str
    task_id: str
    id: str
    message_id: str
    mode: str
    answer: str
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    created_at: int


def _unpack_app(app_model):
    return app_model


def _unpack_caller(caller):
    return caller


@openapi_ns.route("/apps/<string:app_id>/completion-messages")
class CompletionMessagesApi(Resource):
    @APP_PIPELINE.guard(scope="apps:run")
    def post(self, app_id: str, app_model: App, caller, caller_kind: str):
        app = _unpack_app(app_model)
        if AppMode.value_of(app.mode) != AppMode.COMPLETION:
            raise AppUnavailableError()

        body = request.get_json(silent=True) or {}
        body.pop("user", None)
        try:
            payload = CompletionMessageRequest.model_validate(body)
        except ValidationError as exc:
            raise BadRequest(str(exc))
        args = payload.model_dump(exclude_none=True)
        args["auto_generate_name"] = False
        streaming = payload.response_mode == "streaming"

        try:
            response = AppGenerateService.generate(
                app_model=app,
                user=_unpack_caller(caller),
                args=args,
                invoke_from=InvokeFrom.OPENAPI,
                streaming=streaming,
            )
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        except services.errors.conversation.ConversationCompletedError:
            raise ConversationCompletedError()
        except services.errors.app_model_config.AppModelConfigBrokenError:
            logger.exception("App model config broken.")
            raise AppUnavailableError()
        except ProviderTokenNotInitError as ex:
            raise ProviderNotInitializeError(ex.description)
        except QuotaExceededError:
            raise ProviderQuotaExceededError()
        except ModelCurrentlyNotSupportError:
            raise ProviderModelCurrentlyNotSupportError()
        except InvokeError as e:
            raise CompletionRequestError(e.description)
        except ValueError:
            raise
        except Exception:
            logger.exception("internal server error.")
            raise InternalServerError()

        emit_app_run(
            app_id=app.id,
            tenant_id=app.tenant_id,
            caller_kind=caller_kind,
            mode=str(app.mode),
        )

        if streaming:
            return helper.compact_generate_response(response)

        body_dict = response[0] if isinstance(response, tuple) else response
        return CompletionMessageResponse.model_validate(body_dict).model_dump(mode="json"), 200
