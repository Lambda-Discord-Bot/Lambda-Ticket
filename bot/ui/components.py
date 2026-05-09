from __future__ import annotations

import hikari

from bot.core.constants import (
    PANEL_CREATE_BUTTON_ID,
    PANEL_BUTTON_LABEL_INPUT_ID,
    PANEL_DESCRIPTION_INPUT_ID,
    PANEL_TITLE_INPUT_ID,
    TICKET_CLOSE_BUTTON_ID,
    TICKET_REASON_INPUT_ID,
)



def build_panel_button_row(button_label: str) -> hikari.api.MessageActionRowBuilder:
    row = hikari.impl.MessageActionRowBuilder()
    row.add_interactive_button(
        hikari.ButtonStyle.SUCCESS,
        PANEL_CREATE_BUTTON_ID,
        label=(button_label[:80] or "티켓 생성"),
    )
    return row



def build_close_button_row() -> hikari.api.MessageActionRowBuilder:
    row = hikari.impl.MessageActionRowBuilder()
    row.add_interactive_button(
        hikari.ButtonStyle.DANGER,
        TICKET_CLOSE_BUTTON_ID,
        label="티켓 닫기",
    )
    return row



def build_ticket_reason_modal_row(default_value: str = "") -> hikari.api.ModalActionRowBuilder:
    row = hikari.impl.ModalActionRowBuilder()
    row.add_text_input(
        TICKET_REASON_INPUT_ID,
        "문의 내용",
        style=hikari.TextInputStyle.PARAGRAPH,
        placeholder="문의 내용을 자세히 입력해 주세요.",
        value=default_value if default_value else hikari.UNDEFINED,
        min_length=5,
        max_length=500,
    )
    return row



def build_panel_settings_modal_rows(
    title: str,
    description: str,
    button_label: str,
) -> list[hikari.api.ModalActionRowBuilder]:
    title_row = hikari.impl.ModalActionRowBuilder()
    title_row.add_text_input(
        PANEL_TITLE_INPUT_ID,
        "패널 제목",
        placeholder="예: Lambda Ticket Support",
        value=title[:100],
        min_length=1,
        max_length=100,
    )

    description_row = hikari.impl.ModalActionRowBuilder()
    description_row.add_text_input(
        PANEL_DESCRIPTION_INPUT_ID,
        "패널 설명",
        style=hikari.TextInputStyle.PARAGRAPH,
        placeholder="유저에게 보일 안내 문구를 입력해 주세요.",
        value=description[:1024],
        min_length=1,
        max_length=1024,
    )

    button_row = hikari.impl.ModalActionRowBuilder()
    button_row.add_text_input(
        PANEL_BUTTON_LABEL_INPUT_ID,
        "버튼 문구",
        placeholder="예: 티켓 생성",
        value=button_label[:80],
        min_length=1,
        max_length=80,
    )

    return [title_row, description_row, button_row]
