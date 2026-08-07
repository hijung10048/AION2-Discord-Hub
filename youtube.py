from datetime import datetime
from zoneinfo import ZoneInfo

import discord
import feedparser


YOUTUBE_CHANNEL_ID = "UCqh_gleuOIleCy5Qmbo2j1Q"

RSS_URL = (
    "https://www.youtube.com/feeds/videos.xml"
    f"?channel_id={YOUTUBE_CHANNEL_ID}"
)


def format_youtube_time(published: str):
    try:
        dt = datetime.fromisoformat(
            published.replace("Z", "+00:00")
        )

        kst = dt.astimezone(
            ZoneInfo("Asia/Seoul")
        )

        return kst.strftime(
            "%Y년 %m월 %d일 %H:%M"
        )

    except Exception:
        return published


def get_latest_video():
    feed = feedparser.parse(RSS_URL)

    if getattr(feed, "bozo", False):
        print(
            f"[YouTube] RSS 파싱 경고: "
            f"{feed.bozo_exception}"
        )

    if not feed.entries:
        return None

    video = feed.entries[0]

    video_id = video.get(
        "yt_videoid"
    )

    if not video_id:
        return None

    description = video.get(
        "media_description",
        ""
    ).strip()

    if len(description) > 250:
        description = (
            description[:247]
            + "..."
        )

    return {
        "id": video_id,
        "title": video.get(
            "title",
            "제목 없음"
        ),
        "url": video.get(
            "link",
            f"https://www.youtube.com/watch?v={video_id}"
        ),
        "published": format_youtube_time(
            video.get(
                "published",
                ""
            )
        ),
        "description": description,
        "thumbnail": (
            "https://i.ytimg.com/vi/"
            f"{video_id}/hqdefault.jpg"
        )
    }


def create_youtube_embed(video):
    description = (
        "AION2 공식 YouTube에 "
        "새로운 영상이 업로드되었습니다."
    )

    if video["description"]:
        description += (
            "\n\n"
            + video["description"]
        )

    embed = discord.Embed(
        title=video["title"],
        description=description,
        url=video["url"],
        color=0xFF0000
    )

    embed.set_author(
        name="📺 AION2 공식 YouTube"
    )

    embed.set_image(
        url=video["thumbnail"]
    )

    embed.add_field(
        name="🕐 업로드",
        value=video["published"],
        inline=False
    )

    embed.set_footer(
        text="AION2 HUB · 공식 YouTube 알림"
    )

    return embed


def create_youtube_button(video):
    view = discord.ui.View(
        timeout=None
    )

    view.add_item(
        discord.ui.Button(
            label="▶ YouTube에서 보기",
            style=discord.ButtonStyle.link,
            url=video["url"]
        )
    )

    return view