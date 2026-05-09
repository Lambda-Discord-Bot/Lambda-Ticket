from __future__ import annotations

import hikari

from src.database.repositories.guild_settings_repository import GuildSettingsRepository
from src.models.ticket import GuildSettings


class ConfigService:
    def __init__(self, repository: GuildSettingsRepository) -> None:
        self.repository = repository

    async def get_settings(self, guild_id: int) -> GuildSettings:
        return await self.repository.get_settings(guild_id)

    async def set_log_channel(self, guild_id: int, channel_id: int) -> None:
        await self.repository.set_log_channel(guild_id, channel_id)

    async def set_ticket_category(self, guild_id: int, category_id: int) -> None:
        await self.repository.set_ticket_category(guild_id, category_id)

    async def set_panel_channel(self, guild_id: int, channel_id: int) -> None:
        await self.repository.set_panel_channel(guild_id, channel_id)

    async def set_panel_customization(
        self,
        guild_id: int,
        title: str,
        description: str,
        button_label: str,
    ) -> None:
        await self.repository.set_panel_customization(
            guild_id=guild_id,
            panel_title=title,
            panel_description=description,
            panel_button_label=button_label,
        )

    async def get_panel_customization(self, guild_id: int) -> tuple[str, str, str]:
        settings = await self.repository.get_settings(guild_id)
        return settings.panel_title, settings.panel_description, settings.panel_button_label

    async def reset(self, guild_id: int) -> None:
        await self.repository.get_settings(guild_id)
        await self.repository.reset_settings(guild_id)

    async def validate_panel_prerequisites(
        self,
        rest: hikari.api.RESTClient,
        guild_id: int,
    ) -> tuple[bool, str]:
        settings = await self.get_settings(guild_id)

        if settings.log_channel_id is None:
            return False, "로그 채널이 설정되지 않았습니다. `/람다티켓로그`를 먼저 사용해 주세요."
        if settings.ticket_category_id is None:
            return False, "티켓 카테고리가 설정되지 않았습니다. `/람다티켓카테고리`를 먼저 사용해 주세요."

        try:
            log_channel = await rest.fetch_channel(settings.log_channel_id)
            category = await rest.fetch_channel(settings.ticket_category_id)
        except hikari.NotFoundError:
            return False, "저장된 채널 정보를 찾을 수 없습니다. 로그/카테고리를 다시 설정해 주세요."

        if not isinstance(log_channel, hikari.GuildTextChannel):
            return False, "로그 채널은 텍스트 채널이어야 합니다."
        if not isinstance(category, hikari.GuildCategory):
            return False, "티켓 카테고리는 카테고리 채널이어야 합니다."

        return True, ""
