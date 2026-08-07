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

FALLBACK_COUPON_NOTICES = (
    {
        "id": "6a2546841846ff309ba4613f",
        "title": "[안내] AION2 서프라이즈 라이브 쿠폰 안내",
        "url": (
            "https://aion2.plaync.com/ko-kr/board/notice/view"
            "?articleId=6a2546841846ff309ba4613f"
        ),
    },
    {
        "id": "69d4f8c81e8a8c5fcd9b449f",
        "title": "[안내] AION2 시즌3 쿠폰 안내",
        "url": (
            "https://aion2.plaync.com/ko-kr/board/notice/view"
            "?articleId=69d4f8c81e8a8c5fcd9b449f"
        ),
    },
)

CODE_STOPWORDS = {
    "AION2",
    "AION",
    "CHAPTER",
    "NOTICE",
    "EVENT",
    "PLAYNC",
    "NCSOFT",
}

STOP_SECTION_WORDS = (
    "고맙습니다",
    "주의사항",
    "유의사항",
    "안내사항",
    "쿠폰 등록 방법",
    "쿠폰 사용 방법",
)


def _article_id_from_url(url: str) -> str:
    if "articleId=" not in url:
        return ""

    return (
        url
        .split("articleId=", 1)[1]
        .split("&", 1)[0]
    )


async def _collect_coupon_notice_links(page):
    await page.goto(
        NOTICE_LIST_URL,
        wait_until="domcontentloaded",
        timeout=30000,
    )

    await page.wait_for_timeout(4500)

    links = await page.locator(
        'a[href*="/board/notice/view"]'
    ).all()

    coupons = []
    seen_ids = set()

    for link in links:
        href = await link.get_attribute("href")

        if not href or "articleId=" not in href:
            continue

        full_url = urljoin(BASE_URL, href)
        article_id = _article_id_from_url(full_url)

        if not article_id or article_id in seen_ids:
            continue

        title = (await link.inner_text()).strip()

        if not title:
            try:
                title = (
                    await link.locator("xpath=..").inner_text()
                ).strip()
            except Exception:
                title = ""

        if "쿠폰" not in title:
            continue

        coupons.append(
            {
                "id": article_id,
                "title": title,
                "url": full_url,
            }
        )

        seen_ids.add(article_id)

    return coupons


async def _get_best_article_text(page):
    selectors = (
        "article",
        ".article-content",
        ".board-content",
        ".content",
        "[class*='article-content']",
        "[class*='board-content']",
    )

    candidates = []

    for selector in selectors:
        locator = page.locator(selector)

        count = await locator.count()

        for index in range(min(count, 5)):
            try:
                text = (
                    await locator.nth(index).inner_text()
                ).strip()
            except Exception:
                continue

            if len(text) >= 80:
                candidates.append(text)

    if candidates:
        # 가장 내용이 풍부한 게시글 본문 후보를 사용합니다.
        return max(candidates, key=len)

    # 전용 본문 선택자를 못 찾았을 때만 body 전체 사용
    return (
        await page.locator("body").inner_text()
    ).strip()


async def _find_coupon_info_section(page, coupon_code: str = ""):
    """
    페이지 전체가 아니라 실제 '쿠폰 정보' 표/영역에 가장 가까운
    DOM 컨테이너를 찾아 그 텍스트만 반환합니다.
    잘못된 다른 아이템 정보를 보상으로 잡는 것을 막기 위한 함수입니다.
    """
    candidates = []

    labels = page.get_by_text(
        "보상 아이템",
        exact=True,
    )

    count = await labels.count()

    for index in range(count):
        locator = labels.nth(index)

        # 보상 아이템 라벨에서 부모를 조금씩 올라가며
        # 가장 작은 '쿠폰 정보' 컨테이너를 찾습니다.
        current = locator

        for depth in range(1, 9):
            try:
                current = current.locator("xpath=..")
                section_text = (
                    await current.inner_text()
                ).strip()
            except Exception:
                break

            if not section_text:
                continue

            required = (
                "쿠폰 사용 기간",
                "사용 가능 서버",
                "지급 기준",
                "보상 아이템",
            )

            if not all(
                keyword in section_text
                for keyword in required
            ):
                continue

            # 쿠폰 코드까지 같은 컨테이너에 있으면 더 높은 우선순위
            has_code = (
                bool(coupon_code)
                and coupon_code.upper()
                in section_text.upper()
            )

            candidates.append(
                (
                    0 if has_code else 1,
                    len(section_text),
                    section_text,
                )
            )

    if not candidates:
        return ""

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return candidates[0][2]


async def _read_notice_detail(page, notice):
    await page.goto(
        notice["url"],
        wait_until="domcontentloaded",
        timeout=30000,
    )

    await page.wait_for_timeout(2500)

    article_text = await _get_best_article_text(page)
    body_text = (
        await page.locator("body").inner_text()
    ).strip()

    date_match = re.search(
        r"\d{4}-\d{2}-\d{2} "
        r"\d{2}:\d{2}:\d{2}",
        body_text,
    )

    date_text = (
        date_match.group(0)
        if date_match
        else ""
    )

    image_url = None
    og_image = page.locator(
        'meta[property="og:image"]'
    )

    if await og_image.count() > 0:
        image_url = await og_image.get_attribute(
            "content"
        )

    return {
        "id": notice["id"],
        "title": notice["title"],
        "url": notice["url"],
        "date": date_text,
        "content": article_text,
        "body_text": body_text,
        "image": image_url,
    }

def _extract_coupon_codes(text: str):
    upper_text = text.upper()
    codes = []

    targeted_patterns = (
        r"(?:쿠폰\s*(?:코드|번호|명)?\s*[:：]?\s*)"
        r"([A-Z0-9][A-Z0-9_-]{5,31})",
        r"(?:코드\s*[:：]?\s*)"
        r"([A-Z0-9][A-Z0-9_-]{5,31})",
    )

    for pattern in targeted_patterns:
        for match in re.findall(pattern, upper_text):
            if match not in CODE_STOPWORDS and match not in codes:
                codes.append(match)

    # 코드가 단독 라인에 있을 때 보완
    for line in upper_text.splitlines():
        candidate = line.strip()

        if not re.fullmatch(
            r"[A-Z0-9][A-Z0-9_-]{5,31}",
            candidate,
        ):
            continue

        if candidate in CODE_STOPWORDS:
            continue

        # 일반 메뉴/영단어 오탐 억제
        if (
            any(char.isdigit() for char in candidate)
            or candidate.startswith("AION")
        ):
            if candidate not in codes:
                codes.append(candidate)

    return codes[:10]


def _normalize_date_piece(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_expiry(text: str):
    lines = [
        line.strip().lstrip("-").strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # 예:
    # 26년 6월 07일 (일) 17시 00분 ~
    # 26년 7월 8일 (수) 정기점검 전까지
    date_line_pattern = re.compile(
        r"(?:20)?\d{2}\s*년\s*"
        r"\d{1,2}\s*월\s*"
        r"\d{1,2}\s*일"
        r"(?:\s*\([^)]*\))?"
        r"(?:\s*\d{1,2}\s*시\s*\d{1,2}\s*분)?"
        r"(?:\s*(?:~|부터|정기점검\s*전까지|까지))?"
    )

    # '쿠폰 사용 기간' 표 헤더가 있으면 그 뒤에서 날짜 라인을 찾습니다.
    period_header_index = None

    for index, line in enumerate(lines):
        if "쿠폰 사용 기간" in line:
            period_header_index = index
            break

    search_lines = (
        lines[period_header_index + 1:]
        if period_header_index is not None
        else lines
    )

    found = []

    for line in search_lines:
        match = date_line_pattern.search(line)

        if not match:
            continue

        value = re.sub(
            r"\s+",
            " ",
            match.group(0),
        ).strip()

        if value not in found:
            found.append(value)

        # 시작/종료 두 줄이면 충분합니다.
        if len(found) == 2:
            break

    if len(found) >= 2:
        first = found[0].rstrip("~ ").strip()
        second = found[1].strip()
        return f"{first} ~ {second}"

    if len(found) == 1:
        return found[0]

    return ""

def _extract_rewards_from_section(section_text: str):
    if not section_text:
        return []

    lines = [
        re.sub(
            r"\s+",
            " ",
            line.strip().lstrip("-").strip(),
        )
        for line in section_text.splitlines()
        if line.strip()
    ]

    if not lines:
        return []

    # 실제 쿠폰 표의 "보상 아이템" 헤더 위치를 찾습니다.
    try:
        reward_header_index = next(
            index
            for index, line in enumerate(lines)
            if line.replace(" ", "") == "보상아이템"
        )
    except StopIteration:
        return []

    # 보상 표 앞부분의 메타 정보:
    # 수량 / 날짜 2줄 / 전체 서버 / 계정당 1회
    values = lines[reward_header_index + 1:]

    cleaned = []

    for value in values:
        compact = value.replace(" ", "")

        if value == "수량":
            continue

        if compact == "전체서버":
            continue

        if re.fullmatch(
            r"계정당\d+회",
            compact,
        ):
            continue

        if re.search(
            r"(?:20)?\d{2}년"
            r"\d{1,2}월"
            r"\d{1,2}일",
            compact,
        ):
            continue

        if "정기점검전까지" in compact:
            continue

        if value.startswith("상호 (주)엔씨"):
            break

        if "사업자 등록번호" in value:
            break

        if value == "고맙습니다.":
            break

        cleaned.append(value)

    # 이제 실제 구조는
    # 아이템명 -> 수량 -> 아이템명 -> 수량 ...
    rewards = []
    index = 0

    while index < len(cleaned):
        item = cleaned[index]

        # 숫자만 단독으로 먼저 나오면 구조가 깨진 것이므로 건너뜁니다.
        if re.fullmatch(
            r"[\d,]+(?:\s*개)?",
            item,
        ):
            index += 1
            continue

        quantity = ""

        if index + 1 < len(cleaned):
            next_value = cleaned[index + 1]

            if re.fullmatch(
                r"[\d,]+(?:\s*개)?",
                next_value,
            ):
                quantity = next_value
                index += 2
            else:
                index += 1
        else:
            index += 1

        rewards.append(
            {
                "item": item,
                "quantity": quantity,
            }
        )

    return rewards


def _format_rewards_for_embed(rewards):
    if not rewards:
        return "공식 공지에서 확인해주세요."

    lines = []

    for reward in rewards:
        item = reward["item"]
        quantity = reward["quantity"]

        if quantity:
            lines.append(
                f"• {item} × {quantity}"
            )
        else:
            lines.append(
                f"• {item}"
            )

    # Discord embed field value는 1024자 제한.
    result = "\n".join(lines)

    if len(result) <= 1000:
        return result

    # 너무 길면 앞부분만 표시하고 원문 버튼으로 유도.
    short_lines = []
    current_length = 0

    for line in lines:
        addition = len(line) + 1

        if current_length + addition > 900:
            break

        short_lines.append(line)
        current_length += addition

    hidden_count = len(lines) - len(short_lines)

    if hidden_count > 0:
        short_lines.append(
            f"… 외 {hidden_count}개 보상"
        )

    return "\n".join(short_lines)

def _diagnostic_lines(text: str):
    keywords = (
        "쿠폰",
        "기간",
        "기한",
        "보상",
        "지급",
        "등록",
        "사용",
    )

    result = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if any(keyword in line for keyword in keywords):
            result.append(line)

    return result[:30]


async def get_latest_coupon(allow_fallback: bool = True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1920,
                "height": 1080,
            },
            locale="ko-KR",
        )

        try:
            coupons = await _collect_coupon_notice_links(
                page
            )

            if coupons:
                target = coupons[0]
            elif allow_fallback:
                target = FALLBACK_COUPON_NOTICES[0]
            else:
                return None

            detail = await _read_notice_detail(
                page,
                target,
            )

            detail["codes"] = _extract_coupon_codes(
                detail["content"]
            )

            primary_code = (
                detail["codes"][0]
                if detail["codes"]
                else ""
            )

            coupon_info_section = (
                await _find_coupon_info_section(
                    page,
                    primary_code,
                )
            )

            # 기간은 본문 전체에서도 잘 잡히므로 기존 방식 유지
            detail["expiry"] = _extract_expiry(
                detail["content"]
            )

            # 보상은 실제 쿠폰 정보 DOM 영역의 표를
            # 아이템명 + 수량 쌍으로 모두 추출합니다.
            detail["rewards"] = (
                _extract_rewards_from_section(
                    coupon_info_section
                )
            )

            detail["coupon_info_section"] = (
                coupon_info_section
            )

            detail["diagnostic"] = _diagnostic_lines(
                detail["content"]
            )

            return detail

        finally:
            await browser.close()


def create_coupon_embed(coupon):
    embed = discord.Embed(
        title=f"🎁 {coupon['title']}",
        description=(
            "AION2 공식 쿠폰 안내입니다."
        ),
        url=coupon["url"],
        color=0xF1C40F,
    )

    if coupon["codes"]:
        embed.add_field(
            name="🎟️ 쿠폰 코드",
            value="\n".join(
                f"`{code}`"
                for code in coupon["codes"]
            ),
            inline=False,
        )
    else:
        embed.add_field(
            name="🎟️ 쿠폰 코드",
            value="공식 공지에서 확인해주세요.",
            inline=False,
        )

    if coupon["expiry"]:
        embed.add_field(
            name="⏰ 사용 기간",
            value=coupon["expiry"],
            inline=False,
        )

    if coupon["rewards"]:
        embed.add_field(
            name="🎁 보상",
            value=_format_rewards_for_embed(
                coupon["rewards"]
            ),
            inline=False,
        )

    if coupon["date"]:
        embed.add_field(
            name="📅 공지 등록일",
            value=coupon["date"],
            inline=False,
        )

    if coupon["image"]:
        embed.set_image(
            url=coupon["image"]
        )

    embed.set_footer(
        text="AION2 HUB · 공식 쿠폰 알림"
    )

    return embed


def create_coupon_button(coupon):
    view = discord.ui.View(
        timeout=None
    )

    view.add_item(
        discord.ui.Button(
            label="공식 쿠폰 공지 보기",
            style=discord.ButtonStyle.link,
            url=coupon["url"],
        )
    )

    return view


async def main():
    coupon = await get_latest_coupon()

    if coupon is None:
        print("❌ 공식 쿠폰 공지를 찾지 못했습니다.")
        return

    print()
    print("✅ 공식 쿠폰 공지 확인 성공!")
    print()

    print("제목:")
    print(coupon["title"])
    print()

    print("쿠폰 코드:")
    if coupon["codes"]:
        for code in coupon["codes"]:
            print("-", code)
    else:
        print("자동 추출 결과 없음")
    print()

    print("사용 기간:")
    print(coupon["expiry"] or "자동 추출 결과 없음")
    print()

    print("보상:")
    if coupon["rewards"]:
        for reward in coupon["rewards"]:
            if reward["quantity"]:
                print(
                    f"- {reward['item']} × "
                    f"{reward['quantity']}"
                )
            else:
                print(
                    f"- {reward['item']}"
                )
    else:
        print("자동 추출 결과 없음")
    print()

    print("공지 등록일:")
    print(coupon["date"])
    print()

    print("URL:")
    print(coupon["url"])
    print()

    print("----- 실제 쿠폰 정보 영역 -----")
    if coupon.get("coupon_info_section"):
        print(coupon["coupon_info_section"])
    else:
        print("쿠폰 정보 DOM 영역을 찾지 못했습니다.")
    print()

    print("----- 파서 진단용 관련 문장 -----")
    if coupon["diagnostic"]:
        for line in coupon["diagnostic"]:
            print(line)
    else:
        print("관련 문장 없음")


if __name__ == "__main__":
    asyncio.run(main())
