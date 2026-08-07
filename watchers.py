import asyncio

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


def setup_watchers(bot):

    @tasks.loop(minutes=5)
    async def youtube_watcher():
        try:
            video = await asyncio.to_thread(
                get_latest_video
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
                    f"[YouTube] 최초 기준 영상 저장: "
                    f"{video['title']}"
                )
                return

            if last_id == video["id"]:
                return

            print(
                f"[YouTube] 새 영상 발견: "
                f"{video['title']}"
            )

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
                    continue

                channel = guild.get_channel(
                    channel_id
                )

                if channel is None:
                    continue

                try:
                    await channel.send(
                        embed=create_youtube_embed(
                            video
                        ),
                        view=create_youtube_button(
                            video
                        ),
                    )

                    save_youtube_delivery(
                        guild_id,
                        video["id"],
                    )

                    print(
                        f"[YouTube] 전송 완료: "
                        f"{guild.name} → "
                        f"#{channel.name}"
                    )

                except Exception as error:
                    print(
                        f"[YouTube] 전송 실패 "
                        f"({guild_id}): {error}"
                    )

            set_last_youtube_video_id(
                video["id"]
            )

        except Exception as error:
            print(
                f"[YouTube] 자동 확인 오류: "
                f"{error}"
            )

    @youtube_watcher.before_loop
    async def before_youtube_watcher():
        await bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def notice_watcher():
        """
        공지와 점검을 한 번의 홈페이지 조회로 분류합니다.
        점검 공지는 일반 공지 채널에 중복 전송하지 않고
        점검 전용 채널로 라우팅합니다.
        """
        try:
            notice = await get_latest_notice()

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
                    f"[공지] 최초 기준 공지 저장: "
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

            if maintenance:
                print(
                    f"[점검] 새 점검 공지 발견: "
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
                        continue

                    channel = guild.get_channel(
                        channel_id
                    )

                    if channel is None:
                        continue

                    try:
                        await channel.send(
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
                        )

                        save_maintenance_delivery(
                            guild_id,
                            notice["id"],
                        )

                        print(
                            f"[점검] 전송 완료: "
                            f"{guild.name} → "
                            f"#{channel.name}"
                        )

                    except Exception as error:
                        print(
                            f"[점검] 전송 실패 "
                            f"({guild_id}): {error}"
                        )

            else:
                print(
                    f"[공지] 새 공지 발견: "
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
                        continue

                    channel = guild.get_channel(
                        channel_id
                    )

                    if channel is None:
                        continue

                    try:
                        await channel.send(
                            embed=create_notice_embed(
                                notice
                            ),
                            view=create_notice_button(
                                notice
                            ),
                        )

                        save_notice_delivery(
                            guild_id,
                            notice["id"],
                        )

                        print(
                            f"[공지] 전송 완료: "
                            f"{guild.name} → "
                            f"#{channel.name}"
                        )

                    except Exception as error:
                        print(
                            f"[공지] 전송 실패 "
                            f"({guild_id}): {error}"
                        )

            set_last_notice_id(
                notice["id"]
            )

        except Exception as error:
            print(
                f"[공지/점검] 자동 확인 오류: "
                f"{error}"
            )

    @notice_watcher.before_loop
    async def before_notice_watcher():
        await bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def update_watcher():
        try:
            update = await get_latest_update()

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
                    f"[업데이트] 최초 기준 업데이트 저장: "
                    f"{update['title']}"
                )
                return

            if last_id == update["id"]:
                return

            print(
                f"[업데이트] 새 업데이트 발견: "
                f"{update['title']}"
            )

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
                    continue

                channel = guild.get_channel(
                    channel_id
                )

                if channel is None:
                    continue

                try:
                    await channel.send(
                        embed=create_update_embed(
                            update
                        ),
                        view=create_update_button(
                            update
                        ),
                    )

                    save_update_delivery(
                        guild_id,
                        update["id"],
                    )

                    print(
                        f"[업데이트] 전송 완료: "
                        f"{guild.name} → "
                        f"#{channel.name}"
                    )

                except Exception as error:
                    print(
                        f"[업데이트] 전송 실패 "
                        f"({guild_id}): {error}"
                    )

            set_last_update_id(
                update["id"]
            )

        except Exception as error:
            print(
                f"[업데이트] 자동 확인 오류: "
                f"{error}"
            )

    @update_watcher.before_loop
    async def before_update_watcher():
        await bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def coupon_watcher():
        try:
            coupon = await get_latest_coupon(
                allow_fallback=False
            )

            if coupon is None:
                return

            last_id = get_last_coupon_id()

            if last_id == coupon["id"]:
                return

            print(
                f"[쿠폰] 새 쿠폰 발견: "
                f"{coupon['title']}"
            )

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
                    continue

                channel = guild.get_channel(
                    channel_id
                )

                if channel is None:
                    continue

                try:
                    await channel.send(
                        embed=create_coupon_embed(
                            coupon
                        ),
                        view=create_coupon_button(
                            coupon
                        ),
                    )

                    save_coupon_delivery(
                        guild_id,
                        coupon["id"],
                    )

                    print(
                        f"[쿠폰] 전송 완료: "
                        f"{guild.name} → "
                        f"#{channel.name}"
                    )

                except Exception as error:
                    print(
                        f"[쿠폰] 전송 실패 "
                        f"({guild_id}): {error}"
                    )

            set_last_coupon_id(
                coupon["id"]
            )

        except Exception as error:
            print(
                f"[쿠폰] 자동 확인 오류: "
                f"{error}"
            )

    @coupon_watcher.before_loop
    async def before_coupon_watcher():
        await bot.wait_until_ready()

    watchers = {
        "youtube": youtube_watcher,
        "notice": notice_watcher,
        "maintenance": notice_watcher,
        "update": update_watcher,
        "coupon": coupon_watcher,
    }

    bot.aion2_watchers = watchers

    return (
        youtube_watcher,
        notice_watcher,
        update_watcher,
        coupon_watcher,
    )
