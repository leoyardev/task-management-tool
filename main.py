import logging

from fastapi import FastAPI

from src.adapters.api.exception_handlers import domain_exception_handler
from src.adapters.api.v1.routers import project
from src.domain.exceptions.exceptions import DomainException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Task Management API",
        description="Manage tasks and projects with deadline tracking.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_exception_handler(DomainException, domain_exception_handler)

    app.include_router(project.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
