from __future__ import annotations

import hikari



def base_embed(title: str, description: str, *, color: int | None = None) -> hikari.Embed:
    return hikari.Embed(
        title=title,
        description=description,
        color=color if color is not None else 0x5865F2,
    )
