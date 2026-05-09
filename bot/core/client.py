from __future__ import annotations

import logging

import hikari

from bot.commands.ticket_admin import TicketAdminHandler
from bot.config.settings import load_settings
from bot.core.logging import setup_logging
from bot.database.repositories.guild_settings_repository import GuildSettingsRepository
from bot.database.sqlite import SQLiteDatabase
from bot.services.config_service import ConfigService
from bot.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


class LambdaTicketBot:
    def __init__(self) -> None:
        self.settings = load_settings()

        intents = hikari.Intents.GUILDS | hikari.Intents.GUILD_MESSAGES
        self.bot = hikari.GatewayBot(token=self.settings.token, intents=intents)

        self.db = SQLiteDatabase(str(self.settings.sqlite_path))
        self.repo = GuildSettingsRepository(self.db)
        self.config_service = ConfigService(self.repo)
        self.ticket_service = TicketService(self.bot, self.repo, self.settings.data_dir)
        self.handler = TicketAdminHandler(
            bot=self.bot,
            config_service=self.config_service,
            ticket_service=self.ticket_service,
            guild_ids=self.settings.guild_ids,
        )

        self.bot.subscribe(hikari.StartedEvent, self.on_started)
        self.bot.subscribe(hikari.StoppingEvent, self.on_stopping)
        self.bot.subscribe(hikari.InteractionCreateEvent, self.on_interaction_create)

    async def on_started(self, _: hikari.StartedEvent) -> None:
        await self.db.connect()
        await self.repo.initialize()
        await self.handler.sync_commands()

        me = self.bot.get_me()
        if me is not None:
            logger.info("봇 로그인 완료: %s (%s)", me.username, me.id)
        else:
            logger.info("봇 로그인 완료")

    async def on_stopping(self, _: hikari.StoppingEvent) -> None:
        await self.db.close()

    async def on_interaction_create(self, event: hikari.InteractionCreateEvent) -> None:
        interaction = event.interaction

        if isinstance(interaction, hikari.CommandInteraction):
            await self.handler.handle_command_interaction(interaction)
            return

        if isinstance(interaction, hikari.ComponentInteraction):
            await self.handler.handle_component_interaction(interaction)
            return

        if isinstance(interaction, hikari.ModalInteraction):
            await self.handler.handle_modal_interaction(interaction)

    def run(self) -> None:
        self.bot.run()



def run_bot() -> None:
    setup_logging()
    app = LambdaTicketBot()
    app.run()
