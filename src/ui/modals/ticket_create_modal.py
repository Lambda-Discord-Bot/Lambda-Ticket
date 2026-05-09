from __future__ import annotations

from pathlib import Path

import discord

from src.ui.views.ticket_control_view import TicketControlView
from src.utils.embeds import base_embed

PANEL_IMAGE_PATH = Path(__file__).resolve().parents[3] / "assets" / "ticket_panel_image.png"


class TicketCreateModal(discord.ui.Modal, title="티켓 문의 작성"):
    reason = discord.ui.TextInput(
        label="문의 내용",
        placeholder="문의 내용을 자세히 입력해 주세요.",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.client is None:
            await interaction.response.send_message("봇 클라이언트가 준비되지 않았습니다.", ephemeral=True)
            return

        service = getattr(interaction.client, "ticket_service", None)
        if service is None:
            await interaction.response.send_message("티켓 서비스가 준비되지 않았습니다.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        success, message, ticket_channel = await service.create_ticket(interaction, str(self.reason))

        if not success or ticket_channel is None:
            await interaction.followup.send(message, ephemeral=True)
            return

        embed = base_embed(
            title="새 티켓이 생성되었습니다",
            description="",
            color=discord.Color.green(),
        )
        embed.add_field(name="요청자", value=interaction.user.mention, inline=True)
        embed.add_field(name="문의 내용", value=f"```{self.reason}```", inline=False)
        embed.add_field(name="안내", value="추가 내용이 있다면 이 채널에 이어서 보내주세요.", inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()

        if PANEL_IMAGE_PATH.exists():
            image_file = discord.File(PANEL_IMAGE_PATH, filename="ticket_panel_image.png")
            embed.set_thumbnail(url="attachment://ticket_panel_image.png")
            await ticket_channel.send(
                content=f"{interaction.user.mention} 스태프가 곧 확인할 예정입니다.",
                embed=embed,
                view=TicketControlView(),
                file=image_file,
            )
        else:
            await ticket_channel.send(
                content=f"{interaction.user.mention} 스태프가 곧 확인할 예정입니다.",
                embed=embed,
                view=TicketControlView(),
            )

        await interaction.followup.send(f"티켓이 생성되었습니다: {ticket_channel.mention}", ephemeral=True)
