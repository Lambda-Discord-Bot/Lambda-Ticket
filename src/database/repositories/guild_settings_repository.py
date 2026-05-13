from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.database.base import BaseDatabase
from src.models.ticket import GuildSettings, TicketRecord


class GuildSettingsRepository:
    DEFAULT_PANEL_TITLE = "Lambda Ticket Support"
    DEFAULT_PANEL_DESCRIPTION = "아래 버튼을 눌러 문의 티켓을 생성해 주세요."
    DEFAULT_PANEL_BUTTON_LABEL = "티켓 생성"

    def __init__(self, db: BaseDatabase) -> None:
        self.db = db

    async def initialize(self) -> None:
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER,
                ticket_category_id INTEGER,
                panel_channel_id INTEGER,
                panel_title TEXT NOT NULL DEFAULT 'Lambda Ticket Support',
                panel_description TEXT NOT NULL DEFAULT '아래 버튼을 눌러 문의 티켓을 생성해 주세요.',
                panel_button_label TEXT NOT NULL DEFAULT '티켓 생성',
                ticket_index INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self._migrate_guild_settings_columns()
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                status TEXT NOT NULL
            )
            """
        )
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_admin_roles (
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            )
            """
        )

    async def get_settings(self, guild_id: int) -> GuildSettings:
        row = await self.db.fetchone(
            "SELECT * FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        )
        if row is None:
            await self.db.execute(
                "INSERT INTO guild_settings (guild_id) VALUES (?)",
                (guild_id,),
            )
            return GuildSettings(guild_id=guild_id)

        return GuildSettings(
            guild_id=row["guild_id"],
            log_channel_id=row["log_channel_id"],
            ticket_category_id=row["ticket_category_id"],
            panel_channel_id=row["panel_channel_id"],
            panel_title=str(row.get("panel_title") or self.DEFAULT_PANEL_TITLE),
            panel_description=str(row.get("panel_description") or self.DEFAULT_PANEL_DESCRIPTION),
            panel_button_label=str(row.get("panel_button_label") or self.DEFAULT_PANEL_BUTTON_LABEL),
            ticket_index=row["ticket_index"],
        )

    async def set_log_channel(self, guild_id: int, channel_id: int) -> None:
        await self.get_settings(guild_id)
        await self.db.execute(
            "UPDATE guild_settings SET log_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )

    async def set_ticket_category(self, guild_id: int, category_id: int) -> None:
        await self.get_settings(guild_id)
        await self.db.execute(
            "UPDATE guild_settings SET ticket_category_id = ? WHERE guild_id = ?",
            (category_id, guild_id),
        )

    async def set_panel_channel(self, guild_id: int, channel_id: int) -> None:
        await self.get_settings(guild_id)
        await self.db.execute(
            "UPDATE guild_settings SET panel_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )

    async def set_panel_customization(
        self,
        guild_id: int,
        panel_title: str,
        panel_description: str,
        panel_button_label: str,
    ) -> None:
        await self.get_settings(guild_id)
        await self.db.execute(
            """
            UPDATE guild_settings
            SET panel_title = ?,
                panel_description = ?,
                panel_button_label = ?
            WHERE guild_id = ?
            """,
            (panel_title, panel_description, panel_button_label, guild_id),
        )

    async def reset_settings(self, guild_id: int) -> None:
        await self.db.execute(
            """
            UPDATE guild_settings
            SET log_channel_id = NULL,
                ticket_category_id = NULL,
                panel_channel_id = NULL,
                panel_title = ?,
                panel_description = ?,
                panel_button_label = ?,
                ticket_index = 0
            WHERE guild_id = ?
            """,
            (
                self.DEFAULT_PANEL_TITLE,
                self.DEFAULT_PANEL_DESCRIPTION,
                self.DEFAULT_PANEL_BUTTON_LABEL,
                guild_id,
            ),
        )

    async def increment_ticket_index(self, guild_id: int) -> int:
        settings = await self.get_settings(guild_id)
        next_index = settings.ticket_index + 1
        await self.db.execute(
            "UPDATE guild_settings SET ticket_index = ? WHERE guild_id = ?",
            (next_index, guild_id),
        )
        return next_index

    async def add_admin_role(self, guild_id: int, role_id: int) -> None:
        await self.db.execute(
            """
            INSERT OR IGNORE INTO ticket_admin_roles (guild_id, role_id)
            VALUES (?, ?)
            """,
            (guild_id, role_id),
        )

    async def remove_admin_role(self, guild_id: int, role_id: int) -> None:
        await self.db.execute(
            """
            DELETE FROM ticket_admin_roles
            WHERE guild_id = ? AND role_id = ?
            """,
            (guild_id, role_id),
        )

    async def list_admin_role_ids(self, guild_id: int) -> list[int]:
        rows = await self.db.fetchall(
            """
            SELECT role_id
            FROM ticket_admin_roles
            WHERE guild_id = ?
            ORDER BY role_id ASC
            """,
            (guild_id,),
        )
        return [int(row["role_id"]) for row in rows]

    async def add_ticket(self, channel_id: int, guild_id: int, user_id: int, reason: str) -> None:
        await self.db.execute(
            """
            INSERT INTO tickets (ticket_channel_id, guild_id, user_id, reason, opened_at, status)
            VALUES (?, ?, ?, ?, ?, 'open')
            """,
            (channel_id, guild_id, user_id, reason, datetime.utcnow().isoformat()),
        )

    async def close_ticket(self, channel_id: int) -> None:
        await self.db.execute(
            "UPDATE tickets SET status = 'closed', closed_at = ? WHERE ticket_channel_id = ?",
            (datetime.utcnow().isoformat(), channel_id),
        )

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[TicketRecord]:
        row = await self.db.fetchone(
            "SELECT * FROM tickets WHERE ticket_channel_id = ?",
            (channel_id,),
        )
        if row is None:
            return None
        return self._to_ticket_record(row)

    async def get_open_ticket_by_user(self, guild_id: int, user_id: int) -> Optional[TicketRecord]:
        row = await self.db.fetchone(
            """
            SELECT * FROM tickets
            WHERE guild_id = ? AND user_id = ? AND status = 'open'
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (guild_id, user_id),
        )
        if row is None:
            return None
        return self._to_ticket_record(row)

    def _to_ticket_record(self, row: dict[str, object]) -> TicketRecord:
        opened_at = datetime.fromisoformat(str(row["opened_at"]))
        closed_at = row["closed_at"]
        parsed_closed = datetime.fromisoformat(str(closed_at)) if closed_at else None

        return TicketRecord(
            ticket_channel_id=int(row["ticket_channel_id"]),
            guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]),
            reason=str(row["reason"]),
            opened_at=opened_at,
            closed_at=parsed_closed,
            status=str(row["status"]),
        )

    async def _migrate_guild_settings_columns(self) -> None:
        columns = await self.db.fetchall("PRAGMA table_info(guild_settings)")
        existing = {str(column["name"]) for column in columns}

        if "panel_title" not in existing:
            await self.db.execute(
                f"""
                ALTER TABLE guild_settings
                ADD COLUMN panel_title TEXT NOT NULL DEFAULT '{self.DEFAULT_PANEL_TITLE}'
                """
            )
        if "panel_description" not in existing:
            await self.db.execute(
                f"""
                ALTER TABLE guild_settings
                ADD COLUMN panel_description TEXT NOT NULL DEFAULT '{self.DEFAULT_PANEL_DESCRIPTION}'
                """
            )
        if "panel_button_label" not in existing:
            await self.db.execute(
                f"""
                ALTER TABLE guild_settings
                ADD COLUMN panel_button_label TEXT NOT NULL DEFAULT '{self.DEFAULT_PANEL_BUTTON_LABEL}'
                """
            )
