from __future__ import annotations

import discord


class TicketControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="티켓 닫기",
        style=discord.ButtonStyle.red,
        custom_id="lambda_ticket:close",
    )
    async def close_ticket_button(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        if interaction.client is None:
            await interaction.response.send_message("봇 클라이언트가 준비되지 않았습니다.", ephemeral=True)
            return

        service = getattr(interaction.client, "ticket_service", None)
        if service is None:
            await interaction.response.send_message("티켓 서비스가 준비되지 않았습니다.", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("텍스트 채널에서만 사용 가능합니다.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        success, message = await service.close_ticket(interaction, channel)
        try:
            await interaction.edit_original_response(content=message)
        except discord.NotFound:
            # Original interaction response can be unavailable if Discord cleared it.
            pass
