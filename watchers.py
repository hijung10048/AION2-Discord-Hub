import asyncio
import gc

import aiohttp
import discord
from discord.ext import tasks

from database import (
    get_youtube_channels,
    get_last_youtube_video_id,
    set_last_youtube_video_id,
    is_youtube_delivered,
    save_youtube_delivery,
    get_notice_channels,
    get_maintenance_channels,
    get_last_notice_id,
    set_last_notice_id,
    is_notice_delivered,
    save_notice_delivery,
    is_maintenance_delivered,
    save_maintenance_delivery,
    get_update_channels,
    get_last_update_id,
    set_last_update_id,
    is_update_delivered,
    save_update_delivery,
    get_coupon_channels,
    get_last_coupon_id,
    set_last_coupon_id,
    is_coupon_delivered,
    save_coupon_delivery,
)

from youtube import (
    get_latest_video,
    create_youtube_embed,
    create_youtube_button,
)

from notice import (
    get_latest_notice,
    create_notice_embed,
    create_notice_button,
)

from update import (
    get_latest_update,
    create_update_embed,
    create_update_button,
)

from coupon import (
    get_latest_coupon,
    create_coupon_embed,
    create_coupon_button,
)

from maintenance import (
    is_maintenance_notice,
    create_maintenance_embed,
    create_maintenance_button,
)


SOURCE_TIMEOUT = 90
BETWEEN_SOURCES_SECONDS = 8


async def _safe_channel_send(
    channel,
    *,
    embed,
    view,
    label: str,
):
    """
    Discord 전송은 한 번만 시도합니다.
    연결이 끊긴 경우 중복 메시지 가능성을 피하기 위해
    같은 루프에서 무작정 재전송하지 않습니다.
    """
    try:
        await channel.send(
            embed=embed,
            view=view,
        )
        return True

    except (
        discord.HTTPException,
        aiohttp.ClientError,
        asyncio.TimeoutError,
    ) as error:
        print(
            f"[{label}] Discord 전송 오류: "
            f"{type(error).__name__}: {error}"
        )
        return False

    except Exception as error:
        print(
            f"[{label}] 예상치 못한 전송 오류: "
            f"{type(error).__name__}: {error}"
        )
        return False


async def _cleanup_pause():
    # Playwright가 Chromium 프로세스를 정리할 시간을 주고
    # Python 쪽 참조도 빠르게 회수합니다.
    gc.collect()
    await asyncio.sleep(
        BETWEEN_SOURCES_SECONDS
    )


def setup_watchers(bot):
    scrape_lock = asyncio.Lock()
    bot.aion2_scrape_lock = scrape_lock

    async def check_youtube():
        try:
            video = await asyncio.wait_for(
                asyncio.to_thread(
                    get_latest_video
                ),
                timeout=SOURCE_TIMEOUT,
            )

            if video is None:
                print(
                    "[YouTube] 최신 영상을 "
                    "불러오지 못했습니다."
                )
                return

            last_id = (
                get_last_youtube_video_id()
            )

            if last_id is None:
                set_last_youtube_video_id(
                    video["id"]
                )
                print(
                    "[YouTube] 최초 기준 영상 저장: "
                    f"{video['title']}"
                )
                return

            if last_id == video["id"]:
                return

            print(
                "[YouTube] 새 영상 발견: "
                f"{video['title']}"
            )

            send_failed = False

            for (
                guild_id,
                channel_id,
            ) in get_youtube_channels():

                if is_youtube_delivered(
                    guild_id,
                    video["id"],
                ):
                    continue

                guild = bot.get_guild(
                    guild_id
                )

                if guild is None:
                    print(
                        "[YouTube] 서버를 찾을 수 없음: "
                        f"{guild_id}"
                    )
                    continue

                channel = guild.get_channel(
                    channel_id
                )

                if channel is None:
                    print(
                        "[YouTube] 채널을 찾을 수 없음: "
                        f"{channel_id}"
                    )
                    continue

                sent = await _safe_channel_send(
                    channel,
                    embed=create_youtube_embed(
                        video
                    ),
                    view=create_youtube_button(
                        video
                    ),
                    label="YouTube",
                )

                if sent:
                    save_youtube_delivery(
                        guild_id,
                        video["id"],
                    )
                    print(
                        "[YouTube] 전송 완료: "
                        f"{guild.name} → "
                        f"#{channel.name}"
                    )
                else:
                    send_failed = True

            # 실제 Discord 전송 오류가 있었다면
            # 다음 5분 주기에 미전송 서버만 재시도합니다.
            if not send_failed:
                set_last_youtube_video_id(
                    video["id"]
                )

        except asyncio.TimeoutError:
            print(
                "[YouTube] 확인 시간 초과 "
                f"({SOURCE_TIMEOUT}초)"
            )
        except Exception as error:
            print(
                "[YouTube] 자동 확인 오류: "
                f"{type(error).__name__}: {error}"
            )

    async def check_notice():
        try:
            async with scrape_lock:
                notice = await asyncio.wait_for(
                    get_latest_notice(),
                    timeout=SOURCE_TIMEOUT,
                )

            if notice is None:
                print(
                    "[공지] 최신 공지를 "
                    "불러오지 못했습니다."
                )
                return

            last_id = get_last_notice_id()

            if last_id is None:
                set_last_notice_id(
                    notice["id"]
                )
                print(
                    "[공지] 최초 기준 공지 저장: "
                    f"{notice['title']}"
                )
                return

            if last_id == notice["id"]:
                return

            maintenance = (
                is_maintenance_notice(
                    notice["title"]
                )
            )

            send_failed = False

            if maintenance:
                print(
                    "[점검] 새 점검 공지 발견: "
                    f"{notice['title']}"
                )

                targets = (
                    get_maintenance_channels()
                )

                for (
                    guild_id,
                    channel_id,
                ) in targets:

                    if is_maintenance_delivered(
                        guild_id,
                        notice["id"],
                    ):
                        continue

                    guild = bot.get_guild(
                        guild_id
                    )

                    if guild is None:
                        print(
                            "[점검] 서버를 찾을 수 없음: "
                            f"{guild_id}"
                        )
                        continue

                    channel = guild.get_channel(
                        channel_id
                    )

                    if channel is None:
                        print(
                            "[점검] 채널을 찾을 수 없음: "
                            f"{channel_id}"
                        )
                        continue

                    sent = await _safe_channel_send(
                        channel,
                        embed=(
                            create_maintenance_embed(
                                notice
                            )
                        ),
                        view=(
                            create_maintenance_button(
                                notice
                            )
                        ),
                        label="점검",
                    )

                    if sent:
                        save_maintenance_delivery(
                            guild_id,
                            notice["id"],
                        )
                        print(
                            "[점검] 전송 완료: "
                            f"{guild.name} → "
                            f"#{channel.name}"
                        )
                    else:
                        send_failed = True

            else:
                print(
                    "[공지] 새 공지 발견: "
                    f"{notice['title']}"
                )

                for (
                    guild_id,
                    channel_id,
                ) in get_notice_channels():

                    if is_notice_delivered(
                        guild_id,
                        notice["id"],
                    ):
                        continue

                    guild = bot.get_guild(
                        guild_id
                    )

                    if guild is None:
                        print(
                            "[공지] 서버를 찾을 수 없음: "
                            f"{guild_id}"
                        )
                        continue

                    channel = guild.get_channel(
                        channel_id
                    )

                    if channel is None:
                        print(
                            "[공지] 채널을 찾을 수 없음: "
                            f"{channel_id}"
                        )
                        continue

                    sent = await _safe_channel_send(
                        channel,
                        embed=create_notice_embed(
                            notice
                        ),
                        view=create_notice_button(
                            notice
                        ),
                        label="공지",
                    )

                    if sent:
                        save_notice_delivery(
                            guild_id,
                            notice["id"],
                        )
                        print(
                            "[공지] 전송 완료: "
                            f"{guild.name} → "
                            f"#{channel.name}"
                        )
                    else:
                        send_failed = True

            if not send_failed:
                set_last_notice_id(
                    notice["id"]
                )

        except asyncio.TimeoutError:
            print(
                "[공지/점검] 확인 시간 초과 "
                f"({SOURCE_TIMEOUT}초)"
            )
        except Exception as error:
            print(
                "[공지/점검] 자동 확인 오류: "
                f"{type(error).__name__}: {error}"
            )

    async def check_update():
        try:
            async with scrape_lock:
                update = await asyncio.wait_for(
                    get_latest_update(),
                    timeout=SOURCE_TIMEOUT,
                )

            if update is None:
                print(
                    "[업데이트] 최신 업데이트를 "
                    "불러오지 못했습니다."
                )
                return

            last_id = get_last_update_id()

            if last_id is None:
                set_last_update_id(
                    update["id"]
                )
                print(
                    "[업데이트] 최초 기준 업데이트 저장: "
                    f"{update['title']}"
                )
                return

            if last_id == update["id"]:
                return

            print(
                "[업데이트] 새 업데이트 발견: "
                f"{update['title']}"
            )

            send_failed = False

            for (
                guild_id,
                channel_id,
            ) in get_update_channels():

                if is_update_delivered(
                    guild_id,
                    update["id"],
                ):
                    continue

                guild = bot.get_guild(
                    guild_id
                )

                if guild is None:
                    print(
                        "[업데이트] 서버를 찾을 수 없음: "
                        f"{guild_id}"
                    )
                    continue

                channel = guild.get_channel(
                    channel_id
                )

                if channel is None:
                    print(
                        "[업데이트] 채널을 찾을 수 없음: "
                        f"{channel_id}"
                    )
                    continue

                sent = await _safe_channel_send(
                    channel,
                    embed=create_update_embed(
                        update
                    ),
                    view=create_update_button(
                        update
                    ),
                    label="업데이트",
                )

                if sent:
                    save_update_delivery(
                        guild_id,
                        update["id"],
                    )
                    print(
                        "[업데이트] 전송 완료: "
                        f"{guild.name} → "
                        f"#{channel.name}"
                    )
                else:
                    send_failed = True

            if not send_failed:
                set_last_update_id(
                    update["id"]
                )

        except asyncio.TimeoutError:
            print(
                "[업데이트] 확인 시간 초과 "
                f"({SOURCE_TIMEOUT}초)"
            )
        except Exception as error:
            print(
                "[업데이트] 자동 확인 오류: "
                f"{type(error).__name__}: {error}"
            )

    async def check_coupon():
        try:
            async with scrape_lock:
                coupon = await asyncio.wait_for(
                    get_latest_coupon(
                        allow_fallback=False
                    ),
                    timeout=SOURCE_TIMEOUT,
                )

            if coupon is None:
                return

            last_id = get_last_coupon_id()

            if last_id == coupon["id"]:
                return

            print(
                "[쿠폰] 새 쿠폰 발견: "
                f"{coupon['title']}"
            )

            send_failed = False

            for (
                guild_id,
                channel_id,
            ) in get_coupon_channels():

                if is_coupon_delivered(
                    guild_id,
                    coupon["id"],
                ):
                    continue

                guild = bot.get_guild(
                    guild_id
                )

                if guild is None:
                    print(
                        "[쿠폰] 서버를 찾을 수 없음: "
                        f"{guild_id}"
                    )
                    continue

                channel = guild.get_channel(
                    channel_id
                )

                if channel is None:
                    print(
                        "[쿠폰] 채널을 찾을 수 없음: "
                        f"{channel_id}"
                    )
                    continue

                sent = await _safe_channel_send(
                    channel,
                    embed=create_coupon_embed(
                        coupon
                    ),
                    view=create_coupon_button(
                        coupon
                    ),
                    label="쿠폰",
                )

                if sent:
                    save_coupon_delivery(
                        guild_id,
                        coupon["id"],
                    )
                    print(
                        "[쿠폰] 전송 완료: "
                        f"{guild.name} → "
                        f"#{channel.name}"
                    )
                else:
                    send_failed = True

            if not send_failed:
                set_last_coupon_id(
                    coupon["id"]
                )

        except asyncio.TimeoutError:
            print(
                "[쿠폰] 확인 시간 초과 "
                f"({SOURCE_TIMEOUT}초)"
            )
        except Exception as error:
            print(
                "[쿠폰] 자동 확인 오류: "
                f"{type(error).__name__}: {error}"
            )

    @tasks.loop(minutes=5)
    async def hub_watcher():
        """
        e2-micro 안정화용 단일 감시 루프.

        기존:
        공지 / 업데이트 / 쿠폰 감시가 동시에 실행되어
        Chromium이 여러 개 겹칠 수 있었음.

        변경:
        YouTube → 공지/점검 → 업데이트 → 쿠폰 순서로
        한 번에 하나씩만 실행.
        """
        print("[감시] 통합 확인 주기 시작")

        await check_youtube()
        await _cleanup_pause()

        await check_notice()
        await _cleanup_pause()

        await check_update()
        await _cleanup_pause()

        await check_coupon()

        gc.collect()
        print("[감시] 통합 확인 주기 완료")

    @hub_watcher.before_loop
    async def before_hub_watcher():
        await bot.wait_until_ready()

    # /정보 명령어와 기존 코드의 호환성을 위해
    # 각 상태 이름이 동일한 통합 watcher를 가리키게 합니다.
    bot.aion2_watchers = {
        "youtube": hub_watcher,
        "notice": hub_watcher,
        "maintenance": hub_watcher,
        "update": hub_watcher,
        "coupon": hub_watcher,
    }

    return hub_watcher
