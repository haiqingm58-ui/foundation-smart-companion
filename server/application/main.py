from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.auth import router as auth_router
from .api.admin import router as admin_router
from .api.teacher import router as teacher_router
from .api.teacher_catalog import router as teacher_catalog_router
from .api.teacher_papers import router as teacher_papers_router
from .api.student import router as student_router
from .api.student_assessment import router as student_assessment_router
from .api.qa import router as qa_router
from .config import Settings, load_settings
from .database import Database, create_database
from .errors import APIError


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or load_settings()
    database = database or create_database(settings.database_url)
    app = FastAPI(title="Foundation Smart Companion API", version="2.0.0")
    app.state.settings = settings
    app.state.database = database

    def success(request: Request, data, message: str = "操作成功") -> JSONResponse:
        return JSONResponse(
            jsonable_encoder({"success": True, "message": message, "data": data, "requestId": request.state.request_id})
        )

    app.state.success = success
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message, "code": exc.code, "requestId": request.state.request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, _exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"success": False, "message": "请检查表单内容", "code": "VALIDATION_ERROR", "requestId": request.state.request_id},
        )

    @app.get("/api/health")
    def health(request: Request):
        return success(request, {"status": "ok", "llmConfigured": bool(settings.llm_api_url and settings.llm_api_key)})

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(teacher_router)
    app.include_router(teacher_catalog_router)
    app.include_router(teacher_papers_router)
    app.include_router(student_router)
    app.include_router(student_assessment_router)
    app.include_router(qa_router)
    return app
