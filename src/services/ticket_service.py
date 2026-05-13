from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

import discord

from src.database.repositories.guild_settings_repository import GuildSettingsRepository
from src.models.ticket import TicketRecord
from src.utils.embeds import base_embed
from src.utils.permissions import can_manage_ticket
from src.utils.time import format_kst_time


class TicketService:
    def __init__(self, repository: GuildSettingsRepository) -> None:
        self.repository = repository

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        reason: str,
    ) -> tuple[bool, str, discord.TextChannel | None]:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return False, "서버에서만 사용할 수 있습니다.", None

        settings = await self.repository.get_settings(interaction.guild.id)
        if settings.ticket_category_id is None:
            return False, "티켓 카테고리가 설정되지 않았습니다.", None

        category_channel = interaction.guild.get_channel(settings.ticket_category_id)
        if not isinstance(category_channel, discord.CategoryChannel):
            return False, "티켓 카테고리 정보를 찾을 수 없습니다. 관리자에게 문의해 주세요.", None

        existing = await self.repository.get_open_ticket_by_user(interaction.guild.id, interaction.user.id)
        if existing is not None:
            existing_channel = interaction.guild.get_channel(existing.ticket_channel_id)
            if isinstance(existing_channel, discord.TextChannel):
                return False, f"이미 열린 티켓이 있습니다: {existing_channel.mention}", None

        bot_member = interaction.guild.me
        if bot_member is None and interaction.client and interaction.client.user:
            bot_member = interaction.guild.get_member(interaction.client.user.id)
        if bot_member is None:
            return False, "봇 멤버 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", None

        ticket_number = await self.repository.increment_ticket_index(interaction.guild.id)
        channel_name = f"ticket-{ticket_number:04d}"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }
        support_role_ids = await self.repository.list_admin_role_ids(interaction.guild.id)
        for role_id in support_role_ids:
            role = interaction.guild.get_role(role_id)
            if role is None:
                continue
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_channels=True,
                manage_messages=True,
            )

        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category_channel,
            overwrites=overwrites,
            topic=f"티켓 생성자: {interaction.user.id} | 사유: {reason}",
            reason=f"티켓 생성 by {interaction.user} ({interaction.user.id})",
        )

        await self.repository.add_ticket(ticket_channel.id, interaction.guild.id, interaction.user.id, reason)
        return True, "티켓이 생성되었습니다.", ticket_channel

    async def close_ticket(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> tuple[bool, str]:
        record = await self.repository.get_ticket_by_channel(channel.id)
        if record is None or record.status != "open":
            return False, "이 채널은 활성 티켓 채널이 아닙니다."

        if not can_manage_ticket(interaction, record.user_id):
            return False, "티켓 생성자 또는 관리 권한이 있는 유저만 닫을 수 있습니다."

        if interaction.guild is None:
            return False, "서버 정보가 없어 처리할 수 없습니다."

        transcript_file = await self._build_transcript_file(channel)
        await self._send_log(interaction.guild, channel, record, transcript_file)

        await self.repository.close_ticket(channel.id)

        try:
            await channel.delete(reason=f"티켓 종료 by {interaction.user} ({interaction.user.id})")
        except discord.HTTPException:
            return False, "로그 저장은 완료했지만 채널 삭제에 실패했습니다. 권한을 확인해 주세요."

        return True, "티켓이 종료되었습니다."

    async def _build_transcript_file(self, channel: discord.TextChannel) -> discord.File:
        lines: list[str] = []
        async for message in channel.history(limit=None, oldest_first=True):
            created = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{message.author} ({message.author.id})"
            content = message.content if message.content else "[텍스트 없음]"
            lines.append(f"[{created}] {author}: {content}")

            for attachment in message.attachments:
                lines.append(f"  - 첨부파일: {attachment.url}")

        if not lines:
            lines.append("(기록된 메시지가 없습니다)")

        raw = "\n".join(lines)
        bytes_io = BytesIO(raw.encode("utf-8"))
        filename = f"transcript-{channel.id}.txt"
        return discord.File(bytes_io, filename=filename)

    async def _send_log(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        record: TicketRecord,
        transcript: discord.File,
    ) -> None:
        settings = await self.repository.get_settings(guild.id)
        if settings.log_channel_id is None:
            return

        log_channel = guild.get_channel(settings.log_channel_id)
        if not isinstance(log_channel, discord.TextChannel):
            return

        owner = guild.get_member(record.user_id)
        owner_text = owner.mention if owner else f"<@{record.user_id}>"

        embed = base_embed(
            title="티켓 종료 로그",
            description="티켓이 종료되어 대화 스크립트를 저장했습니다.",
            color=discord.Color.red(),
        )
        embed.add_field(name="티켓 채널", value=channel.name, inline=False)
        embed.add_field(name="생성자", value=owner_text, inline=False)
        embed.add_field(name="문의 사유", value=record.reason[:1024], inline=False)
        embed.add_field(name="생성 시각(KST)", value=format_kst_time(record.opened_at), inline=True)
        embed.add_field(name="종료 시각(KST)", value=format_kst_time(datetime.now(UTC)), inline=True)

        await log_channel.send(embed=embed, file=transcript)
