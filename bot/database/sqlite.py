from __future__ import annotations

from typing import Any, Iterable, Optional

import aiosqlite

from bot.database.base import BaseDatabase


class SQLiteDatabase(BaseDatabase):
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        conn = self._require_conn()
        await conn.execute(query, tuple(params))
        await conn.commit()

    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> Optional[dict[str, Any]]:
        conn = self._require_conn()
        async with conn.execute(query, tuple(params)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        conn = self._require_conn()
        async with conn.execute(query, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("DB 연결이 초기화되지 않았습니다.")
        return self._conn
