import re

import discord


MAINTENANCE_KEYWORDS = (
    "정기점검",
    "임시점검",
    "긴급점검",
    "점검 안내",
    "점검안내",
    "서버 점검",
)


def is_maintenance_notice(
    title: str,
) -> bool:
    compact = title.replace(" ", "")

    return any(
        keyword.replace(" ", "")
        in compact
        for keyword in MAINTENANCE_KEYWORDS
    )


def _maintenance_summary(content: str):
    if not content:
        return (
            "자세한 점검 내용은 "
            "공식 공지에서 확인해주세요."
        )

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    selected = []

    for line in lines:
        if any(
            keyword in line
            for keyword in (
                "점검",
                "일시",
                "시간",
                "대상",
                "내용",
                "영향",
            )
        ):
            if line not in selected:
                selected.append(line)

        if len(selected) >= 8:
            break

    if not selected:
        text = content[:700]
    else:
        text = "\n".join(
            f"• {line}"
            for line in selected
        )

    if len(text) > 900:
        text = text[:897] + "..."

    return text


def create_maintenance_embed(notice):
    embed = discord.Embed(
        title=f"🔧 {notice['title']}",
        description=_maintenance_summary(
            notice.get("content", "")
        ),
        url=notice["url"],
        color=0xE67E22,
    )

    if notice.get("date"):
        embed.add_field(
            name="📅 등록일",
            value=notice["date"],
            inline=False,
        )

    if notice.get("image"):
        embed.set_image(
            url=notice["image"]
        )

    embed.set_footer(
        text="AION2 HUB · 공식 점검 알림"
    )

    return embed


def create_maintenance_button(notice):
    view = discord.ui.View(
        timeout=None
    )

    view.add_item(
        discord.ui.Button(
            label="🔧 점검 공지 보기",
            style=discord.ButtonStyle.link,
            url=notice["url"],
        )
    )

    return view
