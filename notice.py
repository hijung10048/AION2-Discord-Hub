import asyncio
import re
from urllib.parse import urljoin

import discord
from playwright.async_api import async_playwright


NOTICE_LIST_URL = (
    "https://aion2.plaync.com/"
    "ko-kr/board/notice/list"
)

BASE_URL = "https://aion2.plaync.com"


# =========================================================
# 공지 목록 가져오기
# =========================================================

async def get_notice_list(page):
    print("[공지] AION2 공지 페이지 접속 중...")

    await page.goto(
        NOTICE_LIST_URL,
        wait_until="domcontentloaded",
        timeout=30000
    )

    await page.wait_for_timeout(5000)

    links = await page.locator(
        'a[href*="/board/notice/view"]'
    ).all()

    notices = []
    seen_ids = set()

    for link in links:
        href = await link.get_attribute("href")

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

        is_pinned = (
            "isNotice=1" in full_url
        )

        notices.append({
            "id": article_id,
            "title": title,
            "url": full_url,
            "is_pinned": is_pinned
        })

        seen_ids.add(article_id)

    return notices


# =========================================================
# 공지 상세정보 가져오기
# =========================================================

async def get_notice_detail(page, notice):
    await page.goto(
        notice["url"],
        wait_until="domcontentloaded",
        timeout=30000
    )

    await page.wait_for_timeout(3000)

    # 페이지 전체 텍스트
    body_text = (
        await page.locator("body").inner_text()
    ).strip()

    # 날짜 추출
    date_match = re.search(
        r"\d{4}-\d{2}-\d{2} "
        r"\d{2}:\d{2}:\d{2}",
        body_text
    )

    date_text = (
        date_match.group(0)
        if date_match
        else ""
    )

    # 본문 찾기
    content_text = ""

    content_selectors = [
        "article",
        ".article-content",
        ".board-content",
        ".content",
        "[class*='article']",
    ]

    for selector in content_selectors:
        locator = page.locator(selector)

        if await locator.count() == 0:
            continue

        try:
            text = (
                await locator.first.inner_text()
            ).strip()

            if len(text) > len(content_text):
                content_text = text

        except Exception:
            pass

    # 선택자로 본문을 못 찾으면 전체 텍스트 사용
    if not content_text:
        content_text = body_text

    # 대표 이미지
    image_url = None

    og_image = page.locator(
        'meta[property="og:image"]'
    )

    if await og_image.count() > 0:
        image_url = (
            await og_image.get_attribute(
                "content"
            )
        )

    return {
        "id": notice["id"],
        "title": notice["title"],
        "url": notice["url"],
        "date": date_text,
        "content": content_text,
        "image": image_url,
    }


# =========================================================
# 최신 일반 공지 가져오기
# =========================================================

async def get_latest_notice():
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
            notices = await get_notice_list(
                page
            )

            normal_notices = [
                notice
                for notice in notices
                if not notice["is_pinned"]
            ]

            if not normal_notices:
                return None

            latest = normal_notices[0]

            return await get_notice_detail(
                page,
                latest
            )

        finally:
            await browser.close()


# =========================================================
# Discord 공지 디자인
# =========================================================

def create_notice_embed(notice):
    content = notice["content"]

    # Discord에는 본문 전체 대신 일부만 표시
    if len(content) > 700:
        content = (
            content[:697]
            + "..."
        )

    embed = discord.Embed(
        title=f"📢 {notice['title']}",
        description=content,
        url=notice["url"],
        color=0x3498DB
    )

    if notice["date"]:
        embed.add_field(
            name="📅 등록일",
            value=notice["date"],
            inline=False
        )

    if notice["image"]:
        embed.set_image(
            url=notice["image"]
        )

    embed.set_footer(
        text="AION2 HUB · 공식 공지사항"
    )

    return embed


def create_notice_button(notice):
    view = discord.ui.View(
        timeout=None
    )

    view.add_item(
        discord.ui.Button(
            label="공지 자세히 보기",
            style=discord.ButtonStyle.link,
            url=notice["url"]
        )
    )

    return view


# =========================================================
# 단독 테스트
# =========================================================

async def main():
    notice = await get_latest_notice()

    if notice is None:
        print(
            "❌ 최신 일반 공지를 "
            "찾지 못했습니다."
        )
        return

    print()
    print(
        "✅ 최신 일반 공지 상세 확인 성공!"
    )
    print()

    print("제목:")
    print(notice["title"])
    print()

    print("등록일:")
    print(notice["date"])
    print()

    print("대표 이미지:")
    print(notice["image"])
    print()

    print("URL:")
    print(notice["url"])
    print()


if __name__ == "__main__":
    asyncio.run(main())