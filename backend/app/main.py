"""Aplicação FastAPI do backend. Escuta somente em 127.0.0.1 (ver scripts de inicialização)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import analysis, course, data, drills, learning, speech, system, teaching
from app.config import Settings, get_settings
from app.container import Container, build_container
from app.services.conversation_service import BadRequest, Conflict, Locked, NotFound
from app.services.lesson_service import LessonOutputError
from app.services.llm_service import LLMUnavailable
from app.services.speech_client import SpeechUnavailable

log = logging.getLogger("english_teacher")


def create_app(config: Settings | None = None, container: Container | None = None) -> FastAPI:
    config = config or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or build_container(config)
        log.info("Backend iniciado. Banco em %s", config.db_path)
        yield

    app = FastAPI(title="English Teacher Local API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    _register_error_handlers(app)
    app.include_router(system.router, prefix="/api")
    app.include_router(teaching.router, prefix="/api")
    app.include_router(speech.router, prefix="/api")
    app.include_router(learning.router, prefix="/api")
    app.include_router(course.router, prefix="/api")
    app.include_router(drills.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(data.router, prefix="/api")
    return app


def _error(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message, "code": code})


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound):
        return _error(404, str(exc), "not_found")

    @app.exception_handler(Conflict)
    async def _conflict(_: Request, exc: Conflict):
        return _error(409, str(exc), "conflict")

    @app.exception_handler(Locked)
    async def _locked(_: Request, exc: Locked):
        return _error(403, str(exc), "locked")

    @app.exception_handler(BadRequest)
    async def _bad_request(_: Request, exc: BadRequest):
        return _error(400, str(exc), "bad_request")

    @app.exception_handler(LLMUnavailable)
    async def _llm(_: Request, exc: LLMUnavailable):
        return _error(503, str(exc), exc.code)

    @app.exception_handler(SpeechUnavailable)
    async def _speech(_: Request, exc: SpeechUnavailable):
        return _error(503, str(exc), exc.code)

    @app.exception_handler(LessonOutputError)
    async def _lesson_output(_: Request, exc: LessonOutputError):
        return _error(502, str(exc), "llm_output_invalid")

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError):
        return _error(400, str(exc), "invalid_value")


app = create_app()
