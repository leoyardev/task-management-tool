from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    DomainException,
    InvalidOperationError,
    NotFoundError,
    ProjectCompletionError,
    TaskAlreadyCompletedError,
)


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    if isinstance(exc, NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    if isinstance(exc, DeadlineViolationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    if isinstance(exc, ProjectCompletionError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    if isinstance(exc, TaskAlreadyCompletedError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    if isinstance(exc, InvalidOperationError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    return JSONResponse(status_code=400, content={"detail": str(exc)})
