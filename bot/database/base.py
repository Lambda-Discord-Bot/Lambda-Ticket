from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional


class BaseDatabase(ABC):
    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        raise NotImplementedError

    @abstractmethod
    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> Optional[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        raise NotImplementedError
