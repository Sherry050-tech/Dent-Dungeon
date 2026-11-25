"""One error format for the whole API: {"detail": str, "code": str, "fields"?: {name: message}}.

Raise ``ApiError`` from services and dependencies. Never raise FastAPI's HTTPException
directly, so the frontend can always rely on ``code`` and ``fields``.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_FILE_TYPE",
    422: "VALIDATION_ERROR",
}


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, detail: str, fields: dict[str, str] | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.fields = fields


def _body(detail: str, code: str, fields: dict[str, str] | None = None) -> dict:
    body = {"detail": detail, "code": code}
    if fields:
        body["fields"] = fields
    return body


def _friendly(err: dict) -> str:
    """Turn one Pydantic error into a short message a person can read."""
    kind, ctx = err.get("type", ""), err.get("ctx") or {}
    if kind == "missing":
        return "This field is required"
    if kind == "string_too_short":
        if ctx.get("min_length") == 1:
            return "This field is required"
        return f"Must be at least {ctx.get('min_length')} characters"
    if kind == "string_too_long":
        return f"Must be at most {ctx.get('max_length')} characters"
    message = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
    if "email address" in message.lower():
        return "Enter a valid email address"
    return message


def validation_fields(exc: RequestValidationError) -> dict[str, str]:
    """{"password": "Must be at least 8 characters"}. Always JSON-safe, first message per field."""
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ()) if part not in ("body", "query", "path")]
        name = ".".join(loc) or "body"
        fields.setdefault(name, _friendly(err))
    return fields


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(status_code=exc.status_code, headers=headers,
                            content=_body(exc.detail, exc.code, exc.fields))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422,
                            content=_body("Validation error", "VALIDATION_ERROR", validation_fields(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = _STATUS_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
        return JSONResponse(status_code=exc.status_code, headers=getattr(exc, "headers", None),
                            content=_body(str(exc.detail), code))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_body("Internal server error", "INTERNAL_ERROR"))