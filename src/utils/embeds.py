from __future__ import annotations

import discord



def base_embed(title: str, description: str, *, color: discord.Color | None = None) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blurple(),
    )
