from __future__ import annotations

from dental_agent.config.settings import STORAGE_BACKEND, SYNC_CSV_SQLITE


VALID_BACKENDS = {"csv", "sqlite"}


def normalize_backend(backend: str | None = None) -> str:
    value = (backend or STORAGE_BACKEND or "csv").strip().lower()
    if value not in VALID_BACKENDS:
        return "csv"
    return value


def get_active_backend() -> str:
    return normalize_backend()


def should_sync_csv_sqlite() -> bool:
    return bool(SYNC_CSV_SQLITE)
