import asyncio
import io
import json
import time

import discord

from database import (
    set_channel,
    get_settings,
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


CHANNEL_SPECS = {
    "coupon_channel_id": (
        "🎁 쿠폰",
        "쿠폰채널설정",
    ),
    "notice_channel_id": (
        "📢 공지사항",
        "공지채널설정",
    ),
    "update_channel_id": (
        "🛠 업데이트",
        "업데이트채널설정",
    ),
    "youtube_channel_id": (
        "📺 유튜브",
        "유튜브채널설정",
    ),
    "maintenance_channel_id": (
        "🔧 점검",
        "점검채널설정",
    ),
}


def _can_manage(
    interaction: discord.Interaction,
) -> bool:
    if interaction.guild is None:
        return False

    return (
        interaction.user
        .guild_permissions
        .manage_guild
    )


async def _require_guild(
    interaction: discord.Interaction,
) -> bool:
    if interaction.guild is not None:
        return True

    await interaction.response.send_message(
        "서버 안에서만 사용할 수 있습니다.",
        ephemeral=True,
    )
    return False


async def _require_manager(
    interaction: discord.Interaction,
) -> bool:
    if not await _require_guild(
        interaction
    ):
        return False

    if _can_manage(interaction):
        return True

    await interaction.response.send_message(
        "❌ 이 명령어는 '서버 관리' 권한이 필요합니다.",
        ephemeral=True,
    )
    return False


def _settings_map(settings):
    if settings is None:
        return {
            "coupon_channel_id": None,
            "notice_channel_id": None,
            "update_channel_id": None,
            "youtube_channel_id": None,
            "maintenance_channel_id": None,
        }

    (
        _,
        coupon_id,
        notice_id,
        update_id,
        youtube_id,
        maintenance_id,
    ) = settings

    return {
        "coupon_channel_id": coupon_id,
        "notice_channel_id": notice_id,
        "update_channel_id": update_id,
        "youtube_channel_id": youtube_id,
        "maintenance_channel_id": maintenance_id,
    }


def _channel_label(
    guild,
    channel_id,
):
    if channel_id is None:
        return "❌ 미설정"

    channel = guild.get_channel(
        channel_id
    )

    if channel is None:
        return "⚠️ 채널을 찾을 수 없음"

    return channel.mention


def _format_uptime(seconds: float):
    seconds = int(max(seconds, 0))
    days, remainder = divmod(
        seconds,
        86400,
    )
    hours, remainder = divmod(
        remainder,
        3600,
    )
    minutes, _ = divmod(
        remainder,
        60,
    )

    parts = []

    if days:
        parts.append(
            f"{days}일"
        )

    if hours or days:
        parts.append(
            f"{hours}시간"
        )

    parts.append(
        f"{minutes}분"
    )

    return " ".join(parts)


def setup_commands(bot):

    async def set_current_channel(
        interaction,
        column_name,
        label,
    ):
        if not await _require_manager(
            interaction
        ):
            return

        set_channel(
            interaction.guild.id,
            column_name,
            interaction.channel.id,
        )

        await interaction.response.send_message(
            f"{label} 알림 채널이 "
            f"{interaction.channel.mention} 으로 설정되었습니다.",
            ephemeral=True,
        )

    @bot.tree.command(
        name="핑",
        description="AION2 HUB가 정상 작동하는지 확인합니다."
    )
    async def ping(
        interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            "🏓 AION2 HUB 정상 작동 중입니다!",
            ephemeral=True,
        )

    @bot.tree.command(
        name="쿠폰채널설정",
        description="현재 채널을 쿠폰 알림 채널로 설정합니다."
    )
    async def coupon_channel(
        interaction: discord.Interaction
    ):
        await set_current_channel(
            interaction,
            "coupon_channel_id",
            "🎁 쿠폰",
        )

    @bot.tree.command(
        name="공지채널설정",
        description="현재 채널을 공지사항 알림 채널로 설정합니다."
    )
    async def notice_channel(
        interaction: discord.Interaction
    ):
        await set_current_channel(
            interaction,
            "notice_channel_id",
            "📢 공지사항",
        )

    @bot.tree.command(
        name="업데이트채널설정",
        description="현재 채널을 업데이트 알림 채널로 설정합니다."
    )
    async def update_channel(
        interaction: discord.Interaction
    ):
        await set_current_channel(
            interaction,
            "update_channel_id",
            "🛠 업데이트",
        )

    @bot.tree.command(
        name="유튜브채널설정",
        description="현재 채널을 유튜브 알림 채널로 설정합니다."
    )
    async def youtube_channel(
        interaction: discord.Interaction
    ):
        await set_current_channel(
            interaction,
            "youtube_channel_id",
            "📺 유튜브",
        )

    @bot.tree.command(
        name="점검채널설정",
        description="현재 채널을 점검 알림 채널로 설정합니다."
    )
    async def maintenance_channel(
        interaction: discord.Interaction
    ):
        await set_current_channel(
            interaction,
            "maintenance_channel_id",
            "🔧 점검",
        )

    @bot.tree.command(
        name="설정확인",
        description="현재 서버의 AION2 HUB 설정을 확인합니다."
    )
    async def check_settings(
        interaction: discord.Interaction
    ):
        if not await _require_guild(
            interaction
        ):
            return

        settings = _settings_map(
            get_settings(
                interaction.guild.id
            )
        )

        embed = discord.Embed(
            title="⚙️ AION2 HUB 설정",
            description=(
                "현재 서버의 알림 채널 설정입니다."
            ),
            color=0x5865F2,
        )

        for column_name, (
            label,
            _,
        ) in CHANNEL_SPECS.items():

            embed.add_field(
                name=label,
                value=_channel_label(
                    interaction.guild,
                    settings[column_name],
                ),
                inline=False,
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @bot.tree.command(
        name="정보",
        description="AION2 HUB의 버전과 작동 상태를 확인합니다."
    )
    async def info(
        interaction: discord.Interaction
    ):
        watchers = getattr(
            bot,
            "aion2_watchers",
            {},
        )

        def status(name):
            watcher = watchers.get(name)

            if (
                watcher is not None
                and watcher.is_running()
            ):
                return "🟢 정상"

            return "🔴 중지"

        started = getattr(
            bot,
            "aion2_started_at",
            time.monotonic(),
        )

        embed = discord.Embed(
            title="🤖 AION2 HUB",
            description=(
                "AION2 공식 정보 자동 알림 봇"
            ),
            color=0x5865F2,
        )

        embed.add_field(
            name="📦 버전",
            value=getattr(
                bot,
                "aion2_version",
                "v1.2 Final",
            ),
            inline=False,
        )

        embed.add_field(
            name="📡 자동 감지",
            value=(
                f"📺 YouTube  {status('youtube')}\n"
                f"📢 공지  {status('notice')}\n"
                f"🔧 점검  {status('maintenance')}\n"
                f"🛠 업데이트  {status('update')}\n"
                f"🎁 쿠폰  {status('coupon')}"
            ),
            inline=False,
        )

        embed.add_field(
            name="🌐 Discord",
            value=(
                f"서버 수: **{len(bot.guilds)}개**\n"
                f"Ping: **{round(bot.latency * 1000)}ms**\n"
                f"가동 시간: **"
                f"{_format_uptime(time.monotonic() - started)}**"
            ),
            inline=False,
        )

        embed.set_footer(
            text="AION2 HUB · v1.2 Final"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @bot.tree.command(
        name="설정내보내기",
        description="현재 서버의 알림 채널 설정을 JSON 파일로 백업합니다."
    )
    async def export_settings(
        interaction: discord.Interaction
    ):
        if not await _require_manager(
            interaction
        ):
            return

        settings = _settings_map(
            get_settings(
                interaction.guild.id
            )
        )

        channels = {}

        for column_name, (
            label,
            _,
        ) in CHANNEL_SPECS.items():

            channel_id = settings[
                column_name
            ]

            channel = (
                interaction.guild.get_channel(
                    channel_id
                )
                if channel_id
                else None
            )

            channels[column_name] = {
                "label": label,
                "id": channel_id,
                "name": (
                    channel.name
                    if channel
                    else None
                ),
            }

        payload = {
            "format": "AION2-HUB-settings",
            "version": "1.2",
            "guild": {
                "id": interaction.guild.id,
                "name": interaction.guild.name,
            },
            "channels": channels,
        }

        data = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        file = discord.File(
            io.BytesIO(data),
            filename=(
                f"aion2hub-settings-"
                f"{interaction.guild.id}.json"
            ),
        )

        await interaction.response.send_message(
            "✅ 현재 서버 설정을 백업했습니다.\n"
            "이 파일에는 **봇 토큰이나 비밀번호가 포함되지 않습니다.**",
            file=file,
            ephemeral=True,
        )

    @bot.tree.command(
        name="설정가져오기",
        description="AION2 HUB 설정 백업 JSON 파일을 복원합니다."
    )
    async def import_settings(
        interaction: discord.Interaction,
        backup_file: discord.Attachment,
    ):
        if not await _require_manager(
            interaction
        ):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            raw = await backup_file.read()

            payload = json.loads(
                raw.decode("utf-8")
            )

            if (
                payload.get("format")
                != "AION2-HUB-settings"
            ):
                raise ValueError(
                    "AION2 HUB 설정 백업 파일이 아닙니다."
                )

            channels = payload.get(
                "channels",
                {},
            )

            restored = []
            skipped = []

            for column_name, (
                label,
                _,
            ) in CHANNEL_SPECS.items():

                saved = channels.get(
                    column_name,
                    {},
                )

                saved_id = saved.get("id")
                saved_name = saved.get(
                    "name"
                )

                channel = None

                # 같은 서버라면 기존 ID를 우선 사용
                if saved_id:
                    channel = (
                        interaction.guild
                        .get_channel(
                            int(saved_id)
                        )
                    )

                # 다른 서버로 옮긴 경우 같은 이름의 채널을 찾아 복원
                if (
                    channel is None
                    and saved_name
                ):
                    channel = discord.utils.get(
                        interaction.guild.channels,
                        name=saved_name,
                    )

                if channel is None:
                    skipped.append(
                        f"{label}: 채널을 찾지 못함"
                    )
                    continue

                set_channel(
                    interaction.guild.id,
                    column_name,
                    channel.id,
                )

                restored.append(
                    f"{label}: #{channel.name}"
                )

            lines = [
                "✅ 설정 복원이 완료되었습니다."
            ]

            if restored:
                lines.append(
                    "\n**복원됨**\n"
                    + "\n".join(
                        f"• {item}"
                        for item in restored
                    )
                )

            if skipped:
                lines.append(
                    "\n**확인 필요**\n"
                    + "\n".join(
                        f"• {item}"
                        for item in skipped
                    )
                )

            await interaction.followup.send(
                "\n".join(lines),
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                "❌ 설정 파일을 복원하지 못했습니다.\n"
                f"`{error}`",
                ephemeral=True,
            )

    @bot.tree.command(
        name="유튜브테스트",
        description="AION2 공식 YouTube의 최신 영상을 현재 채널에 테스트합니다."
    )
    async def youtube_test(
        interaction: discord.Interaction
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        try:
            video = await asyncio.to_thread(
                get_latest_video
            )

            if video is None:
                await interaction.followup.send(
                    "❌ 최신 영상을 찾지 못했습니다.",
                    ephemeral=True,
                )
                return

            await interaction.channel.send(
                embed=create_youtube_embed(
                    video
                ),
                view=create_youtube_button(
                    video
                ),
            )

            await interaction.followup.send(
                "✅ 최신 AION2 영상을 불러왔습니다!",
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ 오류가 발생했습니다.\n`{error}`",
                ephemeral=True,
            )

    @bot.tree.command(
        name="유튜브강제테스트",
        description="설정된 유튜브 채널에 최신 영상을 테스트 전송합니다."
    )
    async def youtube_force_test(
        interaction: discord.Interaction
    ):
        if not await _require_guild(
            interaction
        ):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            settings = _settings_map(
                get_settings(
                    interaction.guild.id
                )
            )

            channel_id = settings[
                "youtube_channel_id"
            ]

            if channel_id is None:
                await interaction.followup.send(
                    "❌ 먼저 /유튜브채널설정 을 실행해주세요.",
                    ephemeral=True,
                )
                return

            channel = (
                interaction.guild
                .get_channel(channel_id)
            )

            if channel is None:
                await interaction.followup.send(
                    "❌ 설정된 유튜브 채널을 찾을 수 없습니다.",
                    ephemeral=True,
                )
                return

            video = await asyncio.to_thread(
                get_latest_video
            )

            if video is None:
                await interaction.followup.send(
                    "❌ 최신 영상을 찾지 못했습니다.",
                    ephemeral=True,
                )
                return

            await channel.send(
                embed=create_youtube_embed(
                    video
                ),
                view=create_youtube_button(
                    video
                ),
            )

            await interaction.followup.send(
                "✅ 유튜브 강제 테스트 전송 완료!",
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ 테스트 중 오류가 발생했습니다.\n`{error}`",
                ephemeral=True,
            )

    @bot.tree.command(
        name="공지테스트",
        description="설정된 공지 채널에 최신 공지를 테스트 전송합니다."
    )
    async def notice_test(
        interaction: discord.Interaction
    ):
        if not await _require_guild(
            interaction
        ):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            settings = _settings_map(
                get_settings(
                    interaction.guild.id
                )
            )

            channel_id = settings[
                "notice_channel_id"
            ]

            if channel_id is None:
                await interaction.followup.send(
                    "❌ 먼저 /공지채널설정 을 실행해주세요.",
                    ephemeral=True,
                )
                return

            channel = (
                interaction.guild
                .get_channel(channel_id)
            )

            notice = await get_latest_notice()

            if (
                channel is None
                or notice is None
            ):
                await interaction.followup.send(
                    "❌ 공지 테스트 데이터를 준비하지 못했습니다.",
                    ephemeral=True,
                )
                return

            await channel.send(
                embed=create_notice_embed(
                    notice
                ),
                view=create_notice_button(
                    notice
                ),
            )

            await interaction.followup.send(
                "✅ 최신 AION2 공지를 테스트 전송했습니다!",
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ 공지 테스트 오류:\n`{error}`",
                ephemeral=True,
            )

    @bot.tree.command(
        name="업데이트테스트",
        description="설정된 업데이트 채널에 최신 업데이트를 테스트 전송합니다."
    )
    async def update_test(
        interaction: discord.Interaction
    ):
        if not await _require_guild(
            interaction
        ):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            settings = _settings_map(
                get_settings(
                    interaction.guild.id
                )
            )

            channel_id = settings[
                "update_channel_id"
            ]

            if channel_id is None:
                await interaction.followup.send(
                    "❌ 먼저 /업데이트채널설정 을 실행해주세요.",
                    ephemeral=True,
                )
                return

            channel = (
                interaction.guild
                .get_channel(channel_id)
            )

            update = await get_latest_update()

            if (
                channel is None
                or update is None
            ):
                await interaction.followup.send(
                    "❌ 업데이트 테스트 데이터를 준비하지 못했습니다.",
                    ephemeral=True,
                )
                return

            await channel.send(
                embed=create_update_embed(
                    update
                ),
                view=create_update_button(
                    update
                ),
            )

            await interaction.followup.send(
                "✅ 최신 AION2 업데이트를 테스트 전송했습니다!",
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ 업데이트 테스트 오류:\n`{error}`",
                ephemeral=True,
            )

    @bot.tree.command(
        name="쿠폰테스트",
        description="설정된 쿠폰 채널에 공식 쿠폰 카드를 테스트 전송합니다."
    )
    async def coupon_test(
        interaction: discord.Interaction
    ):
        if not await _require_guild(
            interaction
        ):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            settings = _settings_map(
                get_settings(
                    interaction.guild.id
                )
            )

            channel_id = settings[
                "coupon_channel_id"
            ]

            if channel_id is None:
                await interaction.followup.send(
                    "❌ 먼저 /쿠폰채널설정 을 실행해주세요.",
                    ephemeral=True,
                )
                return

            channel = (
                interaction.guild
                .get_channel(channel_id)
            )

            coupon = await get_latest_coupon(
                allow_fallback=True
            )

            if (
                channel is None
                or coupon is None
            ):
                await interaction.followup.send(
                    "❌ 쿠폰 테스트 데이터를 준비하지 못했습니다.",
                    ephemeral=True,
                )
                return

            await channel.send(
                embed=create_coupon_embed(
                    coupon
                ),
                view=create_coupon_button(
                    coupon
                ),
            )

            await interaction.followup.send(
                "✅ AION2 쿠폰 알림을 테스트 전송했습니다!",
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ 쿠폰 테스트 오류:\n`{error}`",
                ephemeral=True,
            )

    @bot.tree.command(
        name="점검테스트",
        description="점검 알림 카드 표시를 테스트합니다."
    )
    async def maintenance_test(
        interaction: discord.Interaction
    ):
        if not await _require_guild(
            interaction
        ):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            settings = _settings_map(
                get_settings(
                    interaction.guild.id
                )
            )

            channel_id = settings[
                "maintenance_channel_id"
            ]

            if channel_id is None:
                await interaction.followup.send(
                    "❌ 먼저 /점검채널설정 을 실행해주세요.",
                    ephemeral=True,
                )
                return

            channel = (
                interaction.guild
                .get_channel(channel_id)
            )

            notice = await get_latest_notice()

            if (
                channel is None
                or notice is None
            ):
                await interaction.followup.send(
                    "❌ 점검 테스트 데이터를 준비하지 못했습니다.",
                    ephemeral=True,
                )
                return

            if not is_maintenance_notice(
                notice["title"]
            ):
                await interaction.followup.send(
                    "ℹ️ 현재 최신 공지는 점검 공지가 아닙니다.\n"
                    f"최신 공지: **{notice['title']}**\n\n"
                    "실제 자동 알림에서도 이 공지는 "
                    "점검 채널로 전송되지 않습니다.",
                    ephemeral=True,
                )
                return

            await channel.send(
                embed=create_maintenance_embed(
                    notice
                ),
                view=create_maintenance_button(
                    notice
                ),
            )

            await interaction.followup.send(
                "✅ 최신 점검 공지를 테스트 전송했습니다!",
                ephemeral=True,
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ 점검 테스트 오류:\n`{error}`",
                ephemeral=True,
            )
