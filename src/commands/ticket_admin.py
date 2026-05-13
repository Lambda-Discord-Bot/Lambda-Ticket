from __future__ import annotations

from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from src.ui.modals.panel_settings_modal import PanelSettingsModal
from src.ui.views.ticket_panel_view import TicketPanelView
from src.utils.embeds import base_embed
from src.utils.permissions import is_guild_admin

PANEL_IMAGE_PATH = Path(__file__).resolve().parents[2] / "assets" / "ticket_panel_image.png"


class TicketAdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="람다티켓로그", description="티켓 종료 로그를 보낼 채널을 설정합니다.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="로그를 보낼 텍스트 채널")
    async def ticket_log(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        await self.bot.config_service.set_log_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"티켓 로그 채널을 {channel.mention} 으로 설정했습니다.", ephemeral=True)

    @app_commands.command(name="람다티켓카테고리", description="티켓이 생성될 카테고리를 설정합니다.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(category="티켓을 생성할 카테고리")
    async def ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        await self.bot.config_service.set_ticket_category(interaction.guild.id, category.id)
        await interaction.response.send_message(f"티켓 카테고리를 **{category.name}** 으로 설정했습니다.", ephemeral=True)

    @app_commands.command(name="람다티켓패널", description="지정한 채널에 티켓 패널을 전송합니다.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="티켓 패널을 보낼 텍스트 채널")
    async def ticket_panel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        ok, message = await self.bot.config_service.validate_panel_prerequisites(interaction.guild)
        if not ok:
            await interaction.response.send_message(message, ephemeral=True)
            return

        panel_title, panel_description, panel_button_label = await self.bot.config_service.get_panel_customization(
            interaction.guild.id
        )
        embed = base_embed(
            title=panel_title,
            description=panel_description,
            color=discord.Color.blurple(),
        )

        if PANEL_IMAGE_PATH.exists():
            panel_image = discord.File(PANEL_IMAGE_PATH, filename="ticket_panel_image.png")
            embed.set_thumbnail(url="attachment://ticket_panel_image.png")
            await channel.send(embed=embed, view=TicketPanelView(button_label=panel_button_label), file=panel_image)
        else:
            await channel.send(embed=embed, view=TicketPanelView(button_label=panel_button_label))

        await self.bot.config_service.set_panel_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"티켓 패널을 {channel.mention} 에 전송했습니다.", ephemeral=True)

    @app_commands.command(name="람다티켓패널설정", description="모달로 티켓 패널 임베드/버튼 문구를 설정합니다.")
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel_settings(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        title, description, button_label = await self.bot.config_service.get_panel_customization(interaction.guild.id)
        await interaction.response.send_modal(
            PanelSettingsModal(
                default_title=title,
                default_description=description,
                default_button_label=button_label,
            )
        )

    @app_commands.command(name="람다티켓초기화", description="티켓 관련 설정을 모두 초기화합니다.")
    @app_commands.default_permissions(administrator=True)
    async def ticket_reset(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        await self.bot.config_service.reset(interaction.guild.id)
        await interaction.response.send_message("티켓 설정을 모두 초기화했습니다.", ephemeral=True)

    @app_commands.command(name="람다티켓역할추가", description="티켓 채널에서 문의를 확인/답변할 역할을 추가합니다.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="추가할 역할")
    async def ticket_role_add(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        await self.bot.config_service.add_admin_role(interaction.guild.id, role.id)
        await interaction.response.send_message(
            f"{role.mention} 역할을 티켓 답변 역할 목록에 추가했습니다.",
            ephemeral=True,
        )

    @app_commands.command(name="람다티켓역할제거", description="티켓 채널에서 문의를 확인/답변할 역할을 제거합니다.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="제거할 역할")
    async def ticket_role_remove(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        await self.bot.config_service.remove_admin_role(interaction.guild.id, role.id)
        await interaction.response.send_message(
            f"{role.mention} 역할을 티켓 답변 역할 목록에서 제거했습니다.",
            ephemeral=True,
        )

    @app_commands.command(name="람다티켓역할목록", description="티켓 채널에서 문의를 확인/답변할 역할 목록을 확인합니다.")
    @app_commands.default_permissions(administrator=True)
    async def ticket_role_list(self, interaction: discord.Interaction) -> None:
        if not await self._ensure_real_admin(interaction):
            return

        role_ids = await self.bot.config_service.list_admin_role_ids(interaction.guild.id)
        if not role_ids:
            await interaction.response.send_message("등록된 티켓 답변 역할이 없습니다.", ephemeral=True)
            return

        mentions = [f"<@&{role_id}>" for role_id in role_ids]
        await interaction.response.send_message(
            "티켓 답변 역할 목록:\n" + "\n".join(mentions),
            ephemeral=True,
        )

    async def _ensure_real_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용 가능합니다.", ephemeral=True)
            return False
        if not is_guild_admin(interaction):
            await interaction.response.send_message("서버 관리자만 사용할 수 있습니다.", ephemeral=True)
            return False
        return True


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketAdminCommands(bot))
