from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseParser(ABC):
    """
    Abstract interface for all AES API response parsers.

    Each parser accepts raw JSON (dict/list) and produces domain model objects.
    Parsers are stateless — all context is passed via constructor.

    SOLID — Interface Segregation: Each parser only exposes parse().
    SOLID — Dependency Inversion: GraphBuilder depends on this abstraction.
    """

    def __init__(self, raw_data: dict | list, event_key: str, division_id: int):
        self._data = raw_data
        self._event_key = event_key
        self._division_id = division_id

    @abstractmethod
    def parse(self) -> Any:
        """Parse the raw API JSON into domain model objects."""

    def _build_aes_url(self, path: str) -> str:
        """Construct a full AES results URL for traceability."""
        return f"https://results.advancedeventsystems.com/event/{self._event_key}/{path}"

    def _parse_datetime(self, dt_string: str | None) -> datetime | None:
        """Parse AES datetime string '2026-02-07T07:30:00' → datetime."""
        if not dt_string:
            return None
        return datetime.fromisoformat(dt_string)
