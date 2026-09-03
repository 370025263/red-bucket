"""组装 FastAPI：/api/v1 与 HTML。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from redbucket.api.router import API
from redbucket.errors import AppError
from redbucket.gitcheck import require_git
from redbucket.httpjson import error_body
from redbucket.service import RedBucket
from redbucket.settings import Settings
from redbucket.web.routes import WEB, bind_templates

WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    require_git()
    settings = Settings()
    core = RedBucket(settings)
    app.state.core = core
    app.state.settings = settings
    try:
        yield
    finally:
        core.close()


def create_app() -> FastAPI:
    app = FastAPI(title="red-bucket", lifespan=lifespan)
    templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
    bind_templates(templates)
    app.mount(
        "/static",
        StaticFiles(directory=str(WEB_DIR / "static")),
        name="static",
    )
    app.include_router(API)
    app.include_router(WEB)

    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=exc.status,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def request_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        details = []
        for item in exc.errors():
            loc = item.get("loc") or []
            field = str(loc[-1]) if loc else "body"
            details.append(
                {"field": field, "issue": item.get("msg", "invalid")}
            )
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_failed",
                "validation failed",
                details,
            ),
        )

    return app


app = create_app()
