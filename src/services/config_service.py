from __future__ import annotations

import discord

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

    async def add_admin_role(self, guild_id: int, role_id: int) -> None:
        await self.repository.add_admin_role(guild_id, role_id)

    async def remove_admin_role(self, guild_id: int, role_id: int) -> None:
        await self.repository.remove_admin_role(guild_id, role_id)

    async def list_admin_role_ids(self, guild_id: int) -> list[int]:
        return await self.repository.list_admin_role_ids(guild_id)

    async def is_ticket_admin(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True

        role_ids = await self.list_admin_role_ids(member.guild.id)
        if not role_ids:
            return False

        member_role_ids = {role.id for role in member.roles}
        return any(role_id in member_role_ids for role_id in role_ids)

    async def validate_panel_prerequisites(self, guild: discord.Guild) -> tuple[bool, str]:
        settings = await self.get_settings(guild.id)

        if settings.log_channel_id is None:
            return False, "로그 채널이 설정되지 않았습니다. `/람다티켓로그`를 먼저 사용해 주세요."
        if settings.ticket_category_id is None:
            return False, "티켓 카테고리가 설정되지 않았습니다. `/람다티켓카테고리`를 먼저 사용해 주세요."

        log_channel = guild.get_channel(settings.log_channel_id)
        category = guild.get_channel(settings.ticket_category_id)

        if log_channel is None:
            return False, "저장된 로그 채널을 찾을 수 없습니다. `/람다티켓로그`를 다시 설정해 주세요."
        if not isinstance(log_channel, discord.TextChannel):
            return False, "로그 채널은 텍스트 채널이어야 합니다."

        if category is None:
            return False, "저장된 티켓 카테고리를 찾을 수 없습니다. `/람다티켓카테고리`를 다시 설정해 주세요."
        if not isinstance(category, discord.CategoryChannel):
            return False, "티켓 카테고리는 카테고리 채널이어야 합니다."

        return True, ""
