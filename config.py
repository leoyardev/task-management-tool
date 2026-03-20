import os


class AppConfig:
    """
    Application configuration loaded from environment variables.
    """

    database_url: str
    auto_complete_project: bool

    def __init__(self) -> None:
        self.database_url = os.getenv(
            "DATABASE_URL",
            "sqlite:///./data/tasks.db",
        )
        # When True: completing the last open task in a project
        # automatically marks the project as completed.
        # Controlled via AUTO_COMPLETE_PROJECT env var.
        self.auto_complete_project = (
            os.getenv("AUTO_COMPLETE_PROJECT", "false").lower() == "true"
        )
