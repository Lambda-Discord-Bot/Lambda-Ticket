from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import hikari

from bot.core.constants import (
    PANEL_BUTTON_LABEL_INPUT_ID,
    PANEL_CREATE_BUTTON_ID,
    PANEL_DESCRIPTION_INPUT_ID,
    PANEL_SETTINGS_MODAL_ID,
    PANEL_TITLE_INPUT_ID,
    TICKET_CLOSE_BUTTON_ID,
    TICKET_CREATE_MODAL_ID,
    TICKET_REASON_INPUT_ID,
)
from bot.services.config_service import ConfigService
from bot.services.ticket_service import TicketService
from bot.ui.components import (
    build_panel_button_row,
    build_panel_settings_modal_rows,
    build_ticket_reason_modal_row,
)
from bot.utils.embeds import base_embed
from bot.utils.permissions import is_guild_admin

logger = logging.getLogger(__name__)


class TicketAdminHandler:
    def __init__(
        self,
        bot: hikari.GatewayBot,
        config_service: ConfigService,
        ticket_service: TicketService,
        guild_ids: list[int] | None,
    ) -> None:
        self.bot = bot
        self.config_service = config_service
        self.ticket_service = ticket_service
        self.guild_ids = guild_ids
        self.panel_image_path = Path(__file__).resolve().parents[2] / "assets" / "ticket_panel_image.png"

    async def sync_commands(self) -> None:
        application = await self.bot.rest.fetch_application()
        commands = self._build_commands()

        if self.guild_ids:
            await self.bot.rest.set_application_commands(application.id, [])
            for guild_id in self.guild_ids:
                await self.bot.rest.set_application_commands(application.id, commands, guild=guild_id)
            logger.info("길드 스코프 커맨드 동기화 완료: %s", self.guild_ids)
            return

        cache_guild_ids = [int(gid) for gid in self.bot.cache.get_guilds_view().keys()]
        if cache_guild_ids:
            await self.bot.rest.set_application_commands(application.id, [])
            for guild_id in cache_guild_ids:
                await self.bot.rest.set_application_commands(application.id, commands, guild=guild_id)
            logger.info("자동 길드 동기화 완료: %s", cache_guild_ids)
            return

        await self.bot.rest.set_application_commands(application.id, commands)
        logger.info("글로벌 커맨드 동기화 완료")

    def _build_commands(self) -> list[hikari.api.CommandBuilder]:
        return [
            self.bot.rest.slash_command_builder("람다티켓로그", "티켓 종료 로그를 보낼 채널을 설정합니다.").add_option(
                hikari.CommandOption(
                    type=hikari.OptionType.CHANNEL,
                    name="채널",
                    description="텍스트 채널",
                    is_required=True,
                    channel_types=[hikari.ChannelType.GUILD_TEXT],
                )
            ),
            self.bot.rest.slash_command_builder("람다티켓카테고리", "티켓이 생성될 카테고리를 설정합니다.").add_option(
                hikari.CommandOption(
                    type=hikari.OptionType.CHANNEL,
                    name="채널",
                    description="카테고리 채널",
                    is_required=True,
                    channel_types=[hikari.ChannelType.GUILD_CATEGORY],
                )
            ),
            self.bot.rest.slash_command_builder("람다티켓패널", "지정한 채널에 티켓 패널을 전송합니다.").add_option(
                hikari.CommandOption(
                    type=hikari.OptionType.CHANNEL,
                    name="채널",
                    description="텍스트 채널",
                    is_required=True,
                    channel_types=[hikari.ChannelType.GUILD_TEXT],
                )
            ),
            self.bot.rest.slash_command_builder("람다티켓패널설정", "모달로 티켓 패널 임베드/버튼 문구를 설정합니다."),
            self.bot.rest.slash_command_builder("람다티켓초기화", "티켓 관련 설정을 모두 초기화합니다."),
        ]

    async def handle_command_interaction(self, interaction: hikari.CommandInteraction) -> None:
        command_name = interaction.command_name

        if command_name == "람다티켓로그":
            await self._command_ticket_log(interaction)
            return

        if command_name == "람다티켓카테고리":
            await self._command_ticket_category(interaction)
            return

        if command_name == "람다티켓패널":
            await self._command_ticket_panel(interaction)
            return

        if command_name == "람다티켓패널설정":
            await self._command_ticket_panel_settings(interaction)
            return

        if command_name == "람다티켓초기화":
            await self._command_ticket_reset(interaction)

    async def handle_component_interaction(self, interaction: hikari.ComponentInteraction) -> None:
        if interaction.custom_id == PANEL_CREATE_BUTTON_ID:
            await interaction.create_modal_response(
                title="티켓 문의 작성",
                custom_id=TICKET_CREATE_MODAL_ID,
                components=[build_ticket_reason_modal_row()],
            )
            return

        if interaction.custom_id == TICKET_CLOSE_BUTTON_ID:
            await interaction.create_initial_response(
                hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            success, message = await self.ticket_service.close_ticket_from_component(interaction)
            await interaction.edit_initial_response(message)
            return

    async def handle_modal_interaction(self, interaction: hikari.ModalInteraction) -> None:
        if interaction.custom_id == TICKET_CREATE_MODAL_ID:
            reason = self._extract_modal_value(interaction.components, TICKET_REASON_INPUT_ID)
            if len(reason.strip()) < 5:
                await interaction.create_initial_response(
                    hikari.ResponseType.MESSAGE_CREATE,
                    "문의 내용은 최소 5자 이상이어야 합니다.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            await interaction.create_initial_response(
                hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            success, message, ticket_channel_id = await self.ticket_service.create_ticket_from_modal(interaction, reason.strip())
            if success and ticket_channel_id:
                await interaction.edit_initial_response(f"티켓이 생성되었습니다: <#{ticket_channel_id}>")
            else:
                await interaction.edit_initial_response(message)
            return

        if interaction.custom_id == PANEL_SETTINGS_MODAL_ID:
            if interaction.guild_id is None or interaction.member is None:
                await interaction.create_initial_response(
                    hikari.ResponseType.MESSAGE_CREATE,
                    "서버에서만 사용 가능합니다.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            member_perms = interaction.member.permissions
            if not bool(member_perms & hikari.Permissions.ADMINISTRATOR):
                await interaction.create_initial_response(
                    hikari.ResponseType.MESSAGE_CREATE,
                    "서버 관리자만 사용할 수 있습니다.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            panel_title = self._extract_modal_value(interaction.components, PANEL_TITLE_INPUT_ID).strip()
            panel_description = self._extract_modal_value(interaction.components, PANEL_DESCRIPTION_INPUT_ID).strip()
            panel_button_label = self._extract_modal_value(interaction.components, PANEL_BUTTON_LABEL_INPUT_ID).strip()

            await self.config_service.set_panel_customization(
                guild_id=int(interaction.guild_id),
                title=panel_title[:100] or "Lambda Ticket Support",
                description=panel_description[:1024] or "아래 버튼을 눌러 문의 티켓을 생성해 주세요.",
                button_label=panel_button_label[:80] or "티켓 생성",
            )

            await interaction.create_initial_response(
                hikari.ResponseType.MESSAGE_CREATE,
                "패널 설정을 저장했습니다. 이제 `/람다티켓패널`을 사용하면 적용됩니다.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )

    async def _command_ticket_log(self, interaction: hikari.CommandInteraction) -> None:
        if interaction.guild_id is None:
            await self._respond_ephemeral(interaction, "서버에서만 사용 가능합니다.")
            return
        if not is_guild_admin(interaction):
            await self._respond_ephemeral(interaction, "서버 관리자만 사용할 수 있습니다.")
            return

        channel_id = self._extract_channel_option(interaction, "채널")
        if channel_id is None:
            await self._respond_ephemeral(interaction, "채널 옵션을 확인해 주세요.")
            return

        await self.config_service.set_log_channel(int(interaction.guild_id), channel_id)
        await self._respond_ephemeral(interaction, f"티켓 로그 채널을 <#{channel_id}> 으로 설정했습니다.")

    async def _command_ticket_category(self, interaction: hikari.CommandInteraction) -> None:
        if interaction.guild_id is None:
            await self._respond_ephemeral(interaction, "서버에서만 사용 가능합니다.")
            return
        if not is_guild_admin(interaction):
            await self._respond_ephemeral(interaction, "서버 관리자만 사용할 수 있습니다.")
            return

        channel_id = self._extract_channel_option(interaction, "채널")
        if channel_id is None:
            await self._respond_ephemeral(interaction, "채널 옵션을 확인해 주세요.")
            return

        await self.config_service.set_ticket_category(int(interaction.guild_id), channel_id)
        await self._respond_ephemeral(interaction, f"티켓 카테고리를 <#{channel_id}> 으로 설정했습니다.")

    async def _command_ticket_panel(self, interaction: hikari.CommandInteraction) -> None:
        if interaction.guild_id is None:
            await self._respond_ephemeral(interaction, "서버에서만 사용 가능합니다.")
            return
        if not is_guild_admin(interaction):
            await self._respond_ephemeral(interaction, "서버 관리자만 사용할 수 있습니다.")
            return

        target_channel_id = self._extract_channel_option(interaction, "채널")
        if target_channel_id is None:
            await self._respond_ephemeral(interaction, "채널 옵션을 확인해 주세요.")
            return

        ok, message = await self.config_service.validate_panel_prerequisites(self.bot.rest, int(interaction.guild_id))
        if not ok:
            await self._respond_ephemeral(interaction, message)
            return

        panel_title, panel_description, panel_button_label = await self.config_service.get_panel_customization(
            int(interaction.guild_id)
        )
        embed = base_embed(
            title=panel_title,
            description=panel_description,
            color=0x5865F2,
        )

        if self.panel_image_path.exists():
            embed.set_thumbnail("attachment://ticket_panel_image.png")
            await self.bot.rest.create_message(
                target_channel_id,
                embed=embed,
                components=[build_panel_button_row(panel_button_label)],
                attachment=hikari.File(self.panel_image_path, filename="ticket_panel_image.png"),
            )
        else:
            await self.bot.rest.create_message(
                target_channel_id,
                embed=embed,
                components=[build_panel_button_row(panel_button_label)],
            )

        await self.config_service.set_panel_channel(int(interaction.guild_id), target_channel_id)
        await self._respond_ephemeral(interaction, f"티켓 패널을 <#{target_channel_id}> 에 전송했습니다.")

    async def _command_ticket_panel_settings(self, interaction: hikari.CommandInteraction) -> None:
        if interaction.guild_id is None:
            await self._respond_ephemeral(interaction, "서버에서만 사용 가능합니다.")
            return
        if not is_guild_admin(interaction):
            await self._respond_ephemeral(interaction, "서버 관리자만 사용할 수 있습니다.")
            return

        title, description, button_label = await self.config_service.get_panel_customization(int(interaction.guild_id))
        await interaction.create_modal_response(
            title="티켓 패널 설정",
            custom_id=PANEL_SETTINGS_MODAL_ID,
            components=build_panel_settings_modal_rows(title, description, button_label),
        )

    async def _command_ticket_reset(self, interaction: hikari.CommandInteraction) -> None:
        if interaction.guild_id is None:
            await self._respond_ephemeral(interaction, "서버에서만 사용 가능합니다.")
            return
        if not is_guild_admin(interaction):
            await self._respond_ephemeral(interaction, "서버 관리자만 사용할 수 있습니다.")
            return

        await self.config_service.reset(int(interaction.guild_id))
        await self._respond_ephemeral(interaction, "티켓 설정을 모두 초기화했습니다.")

    async def _respond_ephemeral(self, interaction: hikari.CommandInteraction, content: str) -> None:
        await interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            content,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    def _extract_channel_option(self, interaction: hikari.CommandInteraction, option_name: str) -> int | None:
        for option in interaction.options:
            if option.name == option_name and option.value is not None:
                return int(option.value)
        return None

    def _extract_modal_value(
        self,
        components: Iterable[hikari.ModalActionRowComponent],
        custom_id: str,
    ) -> str:
        for row in components:
            for component in row.components:
                if isinstance(component, hikari.TextInputComponent) and component.custom_id == custom_id:
                    return component.value
        return ""
