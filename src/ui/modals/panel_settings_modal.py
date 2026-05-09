from __future__ import annotations

import discord


class PanelSettingsModal(discord.ui.Modal, title="티켓 패널 설정"):
    def __init__(self, default_title: str, default_description: str, default_button_label: str) -> None:
        super().__init__()

        self.panel_title = discord.ui.TextInput(
            label="패널 제목",
            placeholder="예: Lambda Ticket Support",
            default=default_title[:100],
            min_length=1,
            max_length=100,
        )
        self.panel_description = discord.ui.TextInput(
            label="패널 설명",
            placeholder="유저에게 보일 안내 문구를 입력해 주세요.",
            default=default_description[:1024],
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=1024,
        )
        self.button_label = discord.ui.TextInput(
            label="버튼 문구",
            placeholder="예: 티켓 생성",
            default=default_button_label[:80],
            min_length=1,
            max_length=80,
        )

        self.add_item(self.panel_title)
        self.add_item(self.panel_description)
        self.add_item(self.button_label)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.client is None or interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        config_service = getattr(interaction.client, "config_service", None)
        if config_service is None:
            await interaction.response.send_message("설정 서비스가 준비되지 않았습니다.", ephemeral=True)
            return

        await config_service.set_panel_customization(
            guild_id=interaction.guild.id,
            title=str(self.panel_title).strip(),
            description=str(self.panel_description).strip(),
            button_label=str(self.button_label).strip(),
        )

        await interaction.response.send_message(
            "패널 설정을 저장했습니다. 이제 `/람다티켓패널`을 사용하면 적용됩니다.",
            ephemeral=True,
        )
