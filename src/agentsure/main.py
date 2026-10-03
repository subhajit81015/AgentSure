from fastapi import FastAPI

from .agent_api import router as agent_router
from .api import router
from .config import settings
from .db import init_db
from .observability import configure_otel


def create_app() -> FastAPI:
    init_db()

    configure_otel(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        enable_exporter=bool(
            settings.otel_exporter_otlp_endpoint
        ),
    )

    app = FastAPI(
        title="AgentSure",
        version="0.2.0",
        description="Enterprise AI Agent Evaluation and Assurance Platform",
    )

    app.include_router(router)
    app.include_router(agent_router)

    @app.get("/healthz")
    def healthz():
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": "0.2.0",
        }

    return app


app = create_app()
