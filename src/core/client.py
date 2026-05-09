from __future__ import annotations

import logging

import discord
from discord.ext import commands

from src.config.settings import load_settings
from src.core.logging import setup_logging
from src.database.repositories.guild_settings_repository import GuildSettingsRepository
from src.database.sqlite import SQLiteDatabase
from src.services.config_service import ConfigService
from src.services.ticket_service import TicketService
from src.ui.views.ticket_control_view import TicketControlView
from src.ui.views.ticket_panel_view import TicketPanelView

logger = logging.getLogger(__name__)


class LambdaTicketBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True

        super().__init__(command_prefix="!", intents=intents)

        self.settings = load_settings()
        self.db = SQLiteDatabase(str(self.settings.sqlite_path))
        self.repo = GuildSettingsRepository(self.db)
        self.config_service = ConfigService(self.repo)
        self.ticket_service = TicketService(self.repo)
        self._guild_scope_cleanup_done = False

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.repo.initialize()

        await self.load_extension("src.commands.ticket_admin")

        self.add_view(TicketPanelView())
        self.add_view(TicketControlView())

        if self.settings.guild_ids:
            # Prevent duplicate slash commands by removing stale global commands first.
            if self.application_id is not None:
                await self.http.bulk_upsert_global_commands(self.application_id, [])

            for guild_id in self.settings.guild_ids:
                guild_obj = discord.Object(id=guild_id)
                self.tree.clear_commands(guild=guild_obj)
                self.tree.copy_global_to(guild=guild_obj)
                await self.tree.sync(guild=guild_obj)
            logger.info("길드 스코프 커맨드 동기화 완료: %s", self.settings.guild_ids)
        else:
            await self.tree.sync()
            logger.info("글로벌 커맨드 동기화 완료")

    async def on_ready(self) -> None:
        if not self.settings.guild_ids and not self._guild_scope_cleanup_done:
            for guild in self.guilds:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
            self._guild_scope_cleanup_done = True
            logger.info("기존 길드 스코프 명령어 정리 완료")

        if self.user is not None:
            logger.info("봇 로그인 완료: %s (%s)", self.user, self.user.id)

    async def close(self) -> None:
        await self.db.close()
        await super().close()



def run_bot() -> None:
    setup_logging()
    bot = LambdaTicketBot()
    bot.run(bot.settings.token)
