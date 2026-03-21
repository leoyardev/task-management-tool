from datetime import UTC, datetime


def ensure_utc(dt: datetime | None) -> datetime | None:
    """
    SQLite does not store timezone info — it strips tzinfo on write
    and returns naive datetimes on read even when DateTime(timezone=True)
    is declared on the column.

    This function reattaches UTC so domain entities always carry
    timezone-aware datetimes regardless of what the DB returned.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
