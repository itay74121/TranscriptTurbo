from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.meetings import router as meetings_router
from app.core.config import get_settings
from app.core.errors import BadRequestError, UpstreamError, UpstreamTimeoutError


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="TranscriptTurbo API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(BadRequestError)
    def _bad_request(_: Request, exc: BadRequestError):
        return JSONResponse(status_code=400, content={"error": exc.message})

    @app.exception_handler(UpstreamTimeoutError)
    def _upstream_timeout(_: Request, exc: UpstreamTimeoutError):
        return JSONResponse(status_code=504, content={"error": exc.message})

    @app.exception_handler(UpstreamError)
    def _upstream_error(_: Request, exc: UpstreamError):
        return JSONResponse(status_code=502, content={"error": exc.message})

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(meetings_router, prefix="/api", tags=["meetings"])

    return app


app = create_app()

