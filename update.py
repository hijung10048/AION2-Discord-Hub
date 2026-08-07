import asyncio
import re
from urllib.parse import urljoin

import discord
from playwright.async_api import async_playwright


UPDATE_LIST_URL = (
    "https://aion2.plaync.com/"
    "ko-kr/board/update/list"
)

BASE_URL = "https://aion2.plaync.com"


async def get_latest_update():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1920,
                "height": 1080
            },
            locale="ko-KR"
        )

        try:
            print(
                "[업데이트] AION2 업데이트 "
                "페이지 접속 중..."
            )

            await page.goto(
                UPDATE_LIST_URL,
                wait_until="domcontentloaded",
                timeout=30000
            )

            await page.wait_for_timeout(5000)

            links = await page.locator(
                'a[href*="/board/update/view"]'
            ).all()

            updates = []
            seen_ids = set()

            for link in links:
                href = await link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                if "articleId=" not in href:
                    continue

                full_url = urljoin(
                    BASE_URL,
                    href
                )

                article_id = (
                    full_url
                    .split("articleId=", 1)[1]
                    .split("&", 1)[0]
                )

                if article_id in seen_ids:
                    continue

                title = (
                    await link.inner_text()
                ).strip()

                if not title:
                    try:
                        title = (
                            await link.locator(
                                "xpath=.."
                            ).inner_text()
                        ).strip()

                    except Exception:
                        title = ""

                if not title:
                    continue

                updates.append({
                    "id": article_id,
                    "title": title,
                    "url": full_url
                })

                seen_ids.add(article_id)

            if not updates:
                return None

            latest = updates[0]

            await page.goto(
                latest["url"],
                wait_until="domcontentloaded",
                timeout=30000
            )

            await page.wait_for_timeout(2500)

            body_text = (
                await page.locator(
                    "body"
                ).inner_text()
            )

            date_match = re.search(
                r"\d{4}-\d{2}-\d{2} "
                r"\d{2}:\d{2}:\d{2}",
                body_text
            )

            latest["date"] = (
                date_match.group(0)
                if date_match
                else ""
            )

            return latest

        finally:
            await browser.close()


def create_update_embed(update):
    embed = discord.Embed(
        title="🛠 AION2 업데이트 노트",
        description=(
            f"**{update['title']}**\n\n"
            "업데이트 상세 내용은 "
            "공식 홈페이지에서 확인해주세요."
        ),
        url=update["url"],
        color=0x2ECC71
    )

    if update["date"]:
        embed.add_field(
            name="📅 등록일",
            value=update["date"],
            inline=False
        )

    embed.set_footer(
        text="AION2 HUB · 공식 업데이트"
    )

    return embed


def create_update_button(update):
    view = discord.ui.View(
        timeout=None
    )

    view.add_item(
        discord.ui.Button(
            label="업데이트 노트 보기",
            style=discord.ButtonStyle.link,
            url=update["url"]
        )
    )

    return view


async def main():
    update = await get_latest_update()

    if update is None:
        print(
            "❌ 최신 업데이트를 "
            "찾지 못했습니다."
        )
        return

    print()
    print(
        "✅ 최신 업데이트 확인 성공!"
    )
    print()

    print("제목:")
    print(update["title"])
    print()

    print("등록일:")
    print(update["date"])
    print()

    print("Article ID:")
    print(update["id"])
    print()

    print("URL:")
    print(update["url"])


if __name__ == "__main__":
    asyncio.run(main())