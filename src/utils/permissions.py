from __future__ import annotations

import hikari



def is_guild_admin(interaction: hikari.CommandInteraction) -> bool:
    if interaction.guild_id is None or interaction.member is None:
        return False
    return bool(interaction.member.permissions & hikari.Permissions.ADMINISTRATOR)



def can_manage_ticket_component(interaction: hikari.ComponentInteraction, ticket_owner_id: int) -> bool:
    if interaction.member is None:
        return False
    if int(interaction.user.id) == int(ticket_owner_id):
        return True
    perms = interaction.member.permissions
    return bool(perms & hikari.Permissions.ADMINISTRATOR or perms & hikari.Permissions.MANAGE_CHANNELS)
