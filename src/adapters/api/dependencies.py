from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from config import AppConfig
from src.adapters.notification.console_notifier import ConsoleNotificationService
from src.adapters.persistence.repositories.project import SqlProjectRepository
from src.adapters.persistence.repositories.task import SqlTaskRepository
from src.application.project_service import ProjectService
from src.application.task_service import TaskService
from src.infrastructure.database import build_engine, build_session_factory, get_session


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()


def get_db(config: AppConfig = Depends(get_config)) -> Generator[Session, None, None]:
    engine = build_engine(config.database_url)
    factory = build_session_factory(engine)
    with get_session(factory) as session:
        yield session


def get_project_service(
    session: Session = Depends(get_db),
) -> ProjectService:
    return ProjectService(
        project_repo=SqlProjectRepository(session),
        task_repo=SqlTaskRepository(session),
        notification=ConsoleNotificationService(),
    )


def get_task_service(
    session: Session = Depends(get_db),
    config: AppConfig = Depends(get_config),
) -> TaskService:
    return TaskService(
        task_repo=SqlTaskRepository(session),
        project_repo=SqlProjectRepository(session),
        notification=ConsoleNotificationService(),
        auto_complete_project=config.auto_complete_project,
    )
