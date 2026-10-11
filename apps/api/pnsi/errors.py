"""Typed API errors (spec §15): code, safe message, field errors and request_id."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from pnsi.log import get_logger

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
log = get_logger(__name__)


class FieldError(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    field_errors: list[FieldError] = []
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ApiError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"
    message = "La requête est invalide."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        field_errors: list[FieldError] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.field_errors = field_errors or []
        self.headers = headers
        super().__init__(self.message)


class Unauthenticated(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"
    message = "Authentification requise."


class Forbidden(ApiError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "Action non autorisée pour ce rôle."


class NotFound(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Ressource introuvable."


class Conflict(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "version_conflict"
    message = "La ressource a été modifiée entre-temps. Rechargez avant de réessayer."


class TooManyRequests(ApiError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "Trop de tentatives. Réessayez plus tard."


class ServiceUnavailable(ApiError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "dependency_unavailable"
    message = "Un service nécessaire est indisponible."


# Responses documented on every route so the generated client knows the error shape.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)
}


def _body(code: str, message: str, field_errors: list[FieldError] | None = None) -> dict:
    return ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            field_errors=field_errors or [],
            request_id=request_id_var.get(),
        )
    ).model_dump()


def install_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if 8 <= len(incoming) <= 64 and incoming.isascii() else uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(
            _body(exc.code, exc.message, exc.field_errors),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        fields = [
            FieldError(
                field=".".join(str(p) for p in err.get("loc", ()) if p != "body"),
                message=err.get("msg", "invalide"),
            )
            for err in exc.errors()
        ]
        return JSONResponse(
            jsonable_encoder(_body("validation_error", "Données invalides.", fields)),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(StaleDataError)
    async def stale_handler(request: Request, exc: StaleDataError):
        return JSONResponse(_body(Conflict.code, Conflict.message), status_code=409)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Erreur."
        return JSONResponse(_body(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        log.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            _body("internal_error", "Erreur interne. Référence : voir request_id."),
            status_code=500,
        )
