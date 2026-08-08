import os
import time
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db
from bot_commands import setup_commands
from watchers import setup_watchers


VERSION = "v1.2.2 Stable"


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


# DB 생성 / 기존 DB 자동 마이그레이션
init_db()

# 슬래시 명령어 등록
setup_commands(bot)

# e2-micro용 단일 순차 자동 감지
hub_watcher = setup_watchers(bot)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error,
):
    """
    슬래시 명령 예외가 나도 봇 전체가 영향을 받지 않도록
    사용자에게 가능한 범위에서 오류를 알려주고 로그를 남깁니다.
    """
    print(
        "[슬래시 명령 오류] "
        f"{type(error).__name__}: {error}"
    )
    traceback.print_exception(
        type(error),
        error,
        error.__traceback__,
    )

    message = (
        "❌ 명령 처리 중 일시적인 오류가 발생했습니다.\n"
        "잠시 후 다시 시도해주세요."
    )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )
    except Exception as response_error:
        print(
            "[슬래시 오류 응답 실패] "
            f"{type(response_error).__name__}: "
            f"{response_error}"
        )


@bot.event
async def on_ready():
    try:
        # 재연결 때마다 sync하지 않도록 최초 1회만 실행
        if not getattr(
            bot,
            "aion2_commands_synced",
            False,
        ):
            synced = await bot.tree.sync()
            bot.aion2_commands_synced = True

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

        if not hub_watcher.is_running():
            hub_watcher.start()
            print(
                "통합 자동 감지 시작! "
                "(5분 간격 / 순차 실행)"
            )

        print("=" * 45)

    except Exception as error:
        print(
            "[봇 시작 오류] "
            f"{type(error).__name__}: {error}"
        )
        traceback.print_exc()


bot.run(
    TOKEN,
    reconnect=True,
)
