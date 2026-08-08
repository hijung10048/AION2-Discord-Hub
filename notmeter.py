import discord
from discord.ext import tasks
import aiohttp
import json
import os


# NotMeter 업데이트 알림을 보낼 디스코드 채널
CHANNEL_ID = 1535585837297827852

GITHUB_API = (
    "https://api.github.com/repos/"
    "Not4You-Dev/NotMeter-Update/releases/latest"
)

DOWNLOAD_URL = (
    "https://github.com/Not4You-Dev/"
    "NotMeter-Update/releases/latest/download/NotMeter.zip"
)

VERSION_FILE = "notmeter_version.json"


def load_last_version():
    if not os.path.exists(VERSION_FILE):
        return None

    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version")

    except Exception as e:
        print(f"[NotMeter] 버전 파일 읽기 오류: {e}")
        return None


def save_last_version(version):
    try:
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"version": version},
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print(f"[NotMeter] 버전 저장 오류: {e}")


async def check_release(bot):
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AION2-Discord-Hub"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                GITHUB_API,
                headers=headers
            ) as response:

                if response.status != 200:
                    print(
                        f"[NotMeter] GitHub API 오류: "
                        f"{response.status}"
                    )
                    return

                release = await response.json()

        version = release.get("tag_name")

        if not version:
            print(
                "[NotMeter] 버전 정보를 찾지 못했습니다."
            )
            return

        body = (
            release.get("body")
            or "업데이트 내용이 없습니다."
        )

        release_url = release.get("html_url")

        last_version = load_last_version()

        # 처음 실행했을 때는 현재 버전만 저장
        if last_version is None:
            save_last_version(version)

            print(
                f"[NotMeter] 최초 기준 버전 저장: "
                f"{version}"
            )

            return

        # 이미 확인한 버전이면 아무것도 하지 않음
        if version == last_version:
            return

        # 알림 채널 가져오기
        channel = bot.get_channel(CHANNEL_ID)

        if channel is None:
            try:
                channel = await bot.fetch_channel(
                    CHANNEL_ID
                )

            except Exception as e:
                print(
                    f"[NotMeter] 채널 조회 실패: {e}"
                )
                return

        # Discord Embed 글자 수 제한 대응
        if len(body) > 3500:
            body = body[:3500] + "\n..."

        # 업데이트 Embed
        embed = discord.Embed(
            title=f"NotMeter 업데이트 · {version}",
            description=body,
            color=0x5865F2
        )

        embed.set_footer(
            text=(
                "AION2 HUB · "
                "GitHub 자동 업데이트 알림"
            )
        )

        # 버튼
        view = discord.ui.View(
            timeout=None
        )

        if release_url:
            view.add_item(
                discord.ui.Button(
                    label="업데이트 내용",
                    style=discord.ButtonStyle.link,
                    url=release_url,
                    emoji="📋"
                )
            )

        view.add_item(
            discord.ui.Button(
                label="NotMeter 다운로드",
                style=discord.ButtonStyle.link,
                url=DOWNLOAD_URL,
                emoji="📥"
            )
        )

        # Discord 전송
        await channel.send(
            content=(
                "@everyone "
                "**새로운 NotMeter 업데이트가 "
                "등록되었습니다.**"
            ),
            embed=embed,
            view=view
        )

        # 성공적으로 전송된 뒤 버전 저장
        save_last_version(version)

        print(
            f"[NotMeter] 업데이트 알림 전송 완료: "
            f"{version}"
        )

    except Exception as e:
        print(
            f"[NotMeter] 업데이트 확인 오류: {e}"
        )


def setup_notmeter(bot):

    @tasks.loop(minutes=5)
    async def notmeter_update_loop():
        await check_release(bot)

    @notmeter_update_loop.before_loop
    async def before_notmeter_loop():
        await bot.wait_until_ready()

    return notmeter_update_loop