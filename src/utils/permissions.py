from __future__ import annotations

import discord



def is_guild_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or interaction.user is None:
        return False
    if not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.administrator



def can_manage_ticket(interaction: discord.Interaction, ticket_owner_id: int) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.id == ticket_owner_id:
        return True
    perms = interaction.user.guild_permissions
    return perms.manage_channels or perms.administrator
