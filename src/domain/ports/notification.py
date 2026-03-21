from abc import ABC, abstractmethod

from src.domain.events.events import DomainEvent


class NotificationPort(ABC):
    """
    Port — defines what any notification implementation must provide.

    Reacts to domain events by notifying the outside world.
    The actual implementation lives in adapters/notifications/ and is
    injected at startup via dependency injection.
    """

    @abstractmethod
    def notify(self, event: DomainEvent) -> None:
        """
        Handle a domain event.
        Called by the application layer after every command
        that produces events.
        """
        pass
