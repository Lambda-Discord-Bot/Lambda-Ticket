from __future__ import annotations

import discord

from src.ui.modals.ticket_create_modal import TicketCreateModal


class CreateTicketButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, label: str) -> None:
        super().__init__(
            label=label[:80] or "티켓 생성",
            style=discord.ButtonStyle.green,
            custom_id="lambda_ticket:create",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketCreateModal())


class TicketPanelView(discord.ui.View):
    def __init__(self, button_label: str = "티켓 생성") -> None:
        super().__init__(timeout=None)
        self.add_item(CreateTicketButton(button_label))
