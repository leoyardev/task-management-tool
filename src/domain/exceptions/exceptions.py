class DomainException(Exception):
    """Base for all domain exceptions."""


class NotFoundError(DomainException):
    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} '{entity_id}' not found.")
        self.entity = entity
        self.entity_id = entity_id


class DeadlineViolationError(DomainException):
    """Task deadline exceeds its project deadline."""


class ProjectCompletionError(DomainException):
    """Project cannot be completed while tasks are still open."""


class TaskAlreadyCompletedError(DomainException):
    """Task is already completed."""


class InvalidOperationError(DomainException):
    """Operation is not valid in the current state."""
