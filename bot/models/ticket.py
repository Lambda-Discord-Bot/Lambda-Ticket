from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class GuildSettings:
    guild_id: int
    log_channel_id: Optional[int] = None
    ticket_category_id: Optional[int] = None
    panel_channel_id: Optional[int] = None
    panel_title: str = "Lambda Ticket Support"
    panel_description: str = "아래 버튼을 눌러 문의 티켓을 생성해 주세요."
    panel_button_label: str = "티켓 생성"
    ticket_index: int = 0


@dataclass(slots=True)
class TicketRecord:
    ticket_channel_id: int
    guild_id: int
    user_id: int
    reason: str
    opened_at: datetime
    closed_at: Optional[datetime]
    status: str
