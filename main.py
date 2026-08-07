import os
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db
from bot_commands import setup_commands
from watchers import setup_watchers


VERSION = "v1.2 Final"


load_dotenv()

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        ".env 파일에서 DISCORD_TOKEN을 찾을 수 없습니다."
    )

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)

bot.aion2_version = VERSION
bot.aion2_started_at = time.monotonic()


# DB 생성/기존 DB 자동 마이그레이션
init_db()

# 명령어 등록
setup_commands(bot)

# 자동 감지 등록
(
    youtube_watcher,
    notice_watcher,
    update_watcher,
    coupon_watcher,
) = setup_watchers(bot)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()

        print("=" * 45)
        print(
            f"로그인 성공: {bot.user}"
        )
        print(
            f"슬래시 명령어 "
            f"{len(synced)}개 등록 완료!"
        )
        print(
            f"AION2 HUB {VERSION}"
        )

        if not youtube_watcher.is_running():
            youtube_watcher.start()
            print(
                "YouTube 자동 감지 시작! "
                "(5분 간격)"
            )

        if not notice_watcher.is_running():
            notice_watcher.start()
            print(
                "공지/점검 자동 감지 시작! "
                "(5분 간격)"
            )

        if not update_watcher.is_running():
            update_watcher.start()
            print(
                "업데이트 자동 감지 시작! "
                "(5분 간격)"
            )

        if not coupon_watcher.is_running():
            coupon_watcher.start()
            print(
                "쿠폰 자동 감지 시작! "
                "(5분 간격)"
            )

        print("=" * 45)

    except Exception as error:
        print(
            f"봇 시작 오류: {error}"
        )


bot.run(TOKEN)
