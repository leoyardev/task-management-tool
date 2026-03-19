"""
Unit tests for domain_exception_handler.

Verifies correct HTTP status codes and response body
for each domain exception type.
"""

from unittest.mock import MagicMock

import pytest

from src.adapters.api.exception_handlers import domain_exception_handler
from src.domain.exceptions.exceptions import (
    DeadlineViolationError,
    DomainException,
    InvalidOperationError,
    NotFoundError,
    ProjectCompletionError,
    TaskAlreadyCompletedError,
)


@pytest.fixture
def fake_request():
    return MagicMock()


async def handle(request, exc):
    return await domain_exception_handler(request, exc)


class TestStatusCodes:
    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, fake_request):
        response = await handle(fake_request, NotFoundError("Project", "123"))
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deadline_violation_returns_422(self, fake_request):
        response = await handle(
            fake_request, DeadlineViolationError("Deadline exceeded.")
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_project_completion_error_returns_422(self, fake_request):
        response = await handle(
            fake_request, ProjectCompletionError("Tasks still open.")
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_task_already_completed_returns_409(self, fake_request):
        response = await handle(
            fake_request, TaskAlreadyCompletedError("Already done.")
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_operation_returns_409(self, fake_request):
        response = await handle(fake_request, InvalidOperationError("Invalid."))
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_unhandled_domain_exception_returns_400(self, fake_request):
        response = await handle(fake_request, DomainException("Something went wrong."))
        assert response.status_code == 400


class TestResponseBody:
    @pytest.mark.asyncio
    async def test_detail_contains_exception_message(self, fake_request):
        response = await handle(fake_request, NotFoundError("Task", "abc-123"))
        import json

        body = json.loads(response.body)
        assert "detail" in body
        assert "Task" in body["detail"]
        assert "abc-123" in body["detail"]

    @pytest.mark.asyncio
    async def test_detail_contains_message_for_422(self, fake_request):
        response = await handle(
            fake_request, DeadlineViolationError("Deadline exceeded.")
        )
        import json

        body = json.loads(response.body)
        assert body["detail"] == "Deadline exceeded."

    @pytest.mark.asyncio
    async def test_detail_contains_message_for_409(self, fake_request):
        response = await handle(
            fake_request, InvalidOperationError("Already completed.")
        )
        import json

        body = json.loads(response.body)
        assert body["detail"] == "Already completed."

    @pytest.mark.asyncio
    async def test_detail_contains_message_for_400(self, fake_request):
        response = await handle(fake_request, DomainException("Generic error."))
        import json

        body = json.loads(response.body)
        assert body["detail"] == "Generic error."
