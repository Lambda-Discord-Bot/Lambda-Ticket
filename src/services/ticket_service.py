from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import hikari

from src.database.repositories.guild_settings_repository import GuildSettingsRepository
from src.models.ticket import TicketRecord
from src.ui.components import build_close_button_row
from src.utils.embeds import base_embed
from src.utils.permissions import can_manage_ticket_component
from src.utils.time import format_kst_time


class TicketService:
    def __init__(
        self,
        bot: hikari.GatewayBot,
        repository: GuildSettingsRepository,
        assets_dir: Path,
    ) -> None:
        self.bot = bot
        self.repository = repository
        self.assets_dir = assets_dir

    async def create_ticket_from_modal(
        self,
        interaction: hikari.ModalInteraction,
        reason: str,
    ) -> tuple[bool, str, int | None]:
        if interaction.guild_id is None:
            return False, "서버에서만 사용할 수 있습니다.", None

        settings = await self.repository.get_settings(int(interaction.guild_id))
        if settings.ticket_category_id is None:
            return False, "티켓 카테고리가 설정되지 않았습니다.", None

        try:
            category_channel = await self.bot.rest.fetch_channel(settings.ticket_category_id)
        except hikari.NotFoundError:
            return False, "티켓 카테고리 정보를 찾을 수 없습니다. 관리자에게 문의해 주세요.", None

        if not isinstance(category_channel, hikari.GuildCategory):
            return False, "티켓 카테고리 정보가 올바르지 않습니다.", None

        existing = await self.repository.get_open_ticket_by_user(int(interaction.guild_id), int(interaction.user.id))
        if existing is not None:
            try:
                await self.bot.rest.fetch_channel(existing.ticket_channel_id)
            except hikari.NotFoundError:
                pass
            else:
                return False, f"이미 열린 티켓이 있습니다: <#{existing.ticket_channel_id}>", None

        me = self.bot.get_me()
        if me is None:
            me = await self.bot.rest.fetch_my_user()

        ticket_number = await self.repository.increment_ticket_index(int(interaction.guild_id))
        channel_name = f"ticket-{ticket_number:04d}"

        overwrites = [
            hikari.PermissionOverwrite(
                id=interaction.guild_id,
                type=hikari.PermissionOverwriteType.ROLE,
                deny=hikari.Permissions.VIEW_CHANNEL,
            ),
            hikari.PermissionOverwrite(
                id=interaction.user.id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=(
                    hikari.Permissions.VIEW_CHANNEL
                    | hikari.Permissions.SEND_MESSAGES
                    | hikari.Permissions.READ_MESSAGE_HISTORY
                    | hikari.Permissions.ATTACH_FILES
                    | hikari.Permissions.EMBED_LINKS
                ),
            ),
            hikari.PermissionOverwrite(
                id=me.id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=(
                    hikari.Permissions.VIEW_CHANNEL
                    | hikari.Permissions.SEND_MESSAGES
                    | hikari.Permissions.READ_MESSAGE_HISTORY
                    | hikari.Permissions.MANAGE_CHANNELS
                    | hikari.Permissions.MANAGE_MESSAGES
                    | hikari.Permissions.ATTACH_FILES
                    | hikari.Permissions.EMBED_LINKS
                ),
            ),
        ]

        ticket_channel = await self.bot.rest.create_guild_text_channel(
            guild=interaction.guild_id,
            name=channel_name,
            category=category_channel.id,
            permission_overwrites=overwrites,
            topic=f"티켓 생성자: {interaction.user.id} | 사유: {reason}",
            reason=f"티켓 생성 by {interaction.user} ({interaction.user.id})",
        )

        await self.repository.add_ticket(ticket_channel.id, int(interaction.guild_id), int(interaction.user.id), reason)

        open_embed = base_embed(
            title="새 티켓이 생성되었습니다",
            description=f"<@{interaction.user.id}>님의 문의가 접수되었습니다.\n문의 내용: {reason}",
            color=0x57F287,
        )

        await self.bot.rest.create_message(
            ticket_channel.id,
            content=f"<@{interaction.user.id}> 스태프가 곧 확인할 예정입니다.",
            embed=open_embed,
            components=[build_close_button_row()],
        )

        return True, "티켓이 생성되었습니다.", int(ticket_channel.id)

    async def close_ticket_from_component(
        self,
        interaction: hikari.ComponentInteraction,
    ) -> tuple[bool, str]:
        channel_id = int(interaction.channel_id)
        record = await self.repository.get_ticket_by_channel(channel_id)
        if record is None or record.status != "open":
            return False, "이 채널은 활성 티켓 채널이 아닙니다."

        if not can_manage_ticket_component(interaction, record.user_id):
            return False, "티켓 생성자 또는 관리 권한이 있는 유저만 닫을 수 있습니다."

        transcript_file = await self._build_transcript_file(channel_id)
        await self._send_log(interaction.guild_id, channel_id, record, transcript_file)
        await self.repository.close_ticket(channel_id)

        try:
            await self.bot.rest.delete_channel(channel_id, reason=f"티켓 종료 by {interaction.user} ({interaction.user.id})")
        except hikari.HTTPError:
            return False, "로그 저장은 완료했지만 채널 삭제에 실패했습니다. 권한을 확인해 주세요."

        return True, "티켓이 종료되었습니다."

    async def _build_transcript_file(self, channel_id: int) -> hikari.Bytes:
        messages = [message async for message in self.bot.rest.fetch_messages(channel_id).limit(1000)]
        messages.reverse()

        lines: list[str] = []
        for message in messages:
            created = message.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
            author = f"{message.author} ({message.author.id})"
            content = message.content if message.content else "[텍스트 없음]"
            lines.append(f"[{created}] {author}: {content}")

            for attachment in message.attachments:
                lines.append(f"  - 첨부파일: {attachment.url}")

        if not lines:
            lines.append("(기록된 메시지가 없습니다)")

        raw = "\n".join(lines)
        filename = f"transcript-{channel_id}.txt"
        return hikari.Bytes(raw.encode("utf-8"), filename)

    async def _send_log(
        self,
        guild_id: hikari.Snowflake | None,
        ticket_channel_id: int,
        record: TicketRecord,
        transcript: hikari.Bytes,
    ) -> None:
        if guild_id is None:
            return

        settings = await self.repository.get_settings(int(guild_id))
        if settings.log_channel_id is None:
            return

        channel_name = f"#{ticket_channel_id}"
        try:
            channel = await self.bot.rest.fetch_channel(ticket_channel_id)
        except hikari.NotFoundError:
            channel = None
        if isinstance(channel, hikari.GuildTextChannel):
            channel_name = channel.name

        owner_text = f"<@{record.user_id}>"

        embed = base_embed(
            title="티켓 종료 로그",
            description="티켓이 종료되어 대화 스크립트를 저장했습니다.",
            color=0xED4245,
        )
        embed.add_field(name="티켓 채널", value=channel_name, inline=False)
        embed.add_field(name="생성자", value=owner_text, inline=False)
        embed.add_field(name="문의 사유", value=record.reason[:1024], inline=False)
        embed.add_field(name="생성 시각(KST)", value=format_kst_time(record.opened_at), inline=True)
        embed.add_field(name="종료 시각(KST)", value=format_kst_time(datetime.now(UTC)), inline=True)

        await self.bot.rest.create_message(settings.log_channel_id, embed=embed, attachment=transcript)
