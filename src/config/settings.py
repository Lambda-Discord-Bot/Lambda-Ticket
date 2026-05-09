from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values, load_dotenv


@dataclass(slots=True)
class BotSettings:
    token: str
    guild_ids: Optional[list[int]]
    data_dir: Path
    sqlite_path: Path



def _parse_guild_ids(raw: str | None) -> Optional[list[int]]:
    if not raw:
        return None
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        return None
    return [int(value) for value in values]



def load_settings() -> BotSettings:
    base_dir = Path(__file__).resolve().parents[2]
    env_path = base_dir / ".env"
    load_dotenv(env_path, encoding="utf-8-sig")

    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token and env_path.exists():
        # Fallback for BOM-prefixed .env keys
        values = dotenv_values(env_path, encoding="utf-8-sig")
        token = str(values.get("DISCORD_BOT_TOKEN", "")).strip()
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN 값이 없습니다. .env 파일을 확인하세요.")

    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    return BotSettings(
        token=token,
        guild_ids=_parse_guild_ids(os.getenv("DISCORD_GUILD_IDS")),
        data_dir=data_dir,
        sqlite_path=data_dir / "ticket_bot.sqlite3",
    )
