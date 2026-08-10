import json
import re

import aiohttp
import discord


YOUTUBE_CHANNEL_ID = "UCqh_gleuOIleCy5Qmbo2j1Q"

POSTS_URL = (
    f"https://www.youtube.com/channel/"
    f"{YOUTUBE_CHANNEL_ID}/posts"
)


async def fetch_youtube_posts():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            POSTS_URL,
            headers=headers,
            timeout=30,
        ) as response:

            if response.status != 200:
                print(
                    "[YouTube Posts] "
                    f"페이지 조회 실패: {response.status}"
                )
                return []

            html = await response.text()

    match = re.search(
        r"var ytInitialData\s*=\s*({.*?});</script>",
        html,
        re.DOTALL,
    )

    if not match:
        match = re.search(
            r'ytInitialData"\s*:\s*({.*?})\s*,\s*"',
            html,
            re.DOTALL,
        )

    if not match:
        print(
            "[YouTube Posts] "
            "ytInitialData를 찾지 못했습니다."
        )
        return []

    try:
        data = json.loads(
            match.group(1)
        )

    except Exception as e:
        print(
            "[YouTube Posts] "
            f"JSON 파싱 실패: {e}"
        )
        return []

    posts = []

    find_posts_recursive(
        data,
        posts,
    )

    return posts


def find_posts_recursive(data, posts):
    if isinstance(data, dict):

        # 현재 YouTube 커뮤니티 게시글 구조
        renderer = data.get(
            "backstagePostRenderer"
        )

        if renderer:
            parse_post_renderer(
                renderer,
                posts,
            )

        # 일부 구조에서 사용하는 게시글 렌더러
        renderer = data.get(
            "postRenderer"
        )

        if renderer:
            parse_post_renderer(
                renderer,
                posts,
            )

        # 내부 데이터를 계속 재귀 탐색
        for value in data.values():
            find_posts_recursive(
                value,
                posts,
            )

    elif isinstance(data, list):

        for item in data:
            find_posts_recursive(
                item,
                posts,
            )

def parse_post_renderer(renderer, posts):
    post_id = (
        renderer.get("postId")
        or renderer.get("targetId")
    )

    if not post_id:
        return

    content_text = ""

    content = renderer.get(
        "contentText",
        {}
    )

    runs = content.get(
        "runs",
        []
    )

    if runs:
        content_text = "".join(
            run.get("text", "")
            for run in runs
        ).strip()

    if not content_text:
        content_text = "새로운 YouTube 게시글"

    published = ""

    published_text = renderer.get(
        "publishedTimeText",
        {}
    )

    if published_text:
        published = published_text.get(
            "simpleText",
            ""
        )

    post_url = (
        "https://www.youtube.com/post/"
        + post_id
    )

    image_url = find_image_url(
        renderer
    )

    post = {
        "id": post_id,
        "text": content_text,
        "published": published,
        "url": post_url,
        "image": image_url,
    }

    if not any(
        existing["id"] == post_id
        for existing in posts
    ):
        posts.append(post)


def find_image_url(data):
    images = []

    collect_images(
        data,
        images,
    )

    if not images:
        return None

    images.sort(
        key=lambda image: (
            image.get("width", 0)
            * image.get("height", 0)
        ),
        reverse=True,
    )

    return images[0].get(
        "url"
    )


def collect_images(data, images):
    if isinstance(data, dict):

        thumbnails = data.get(
            "thumbnails"
        )

        if isinstance(
            thumbnails,
            list,
        ):
            for thumbnail in thumbnails:

                url = thumbnail.get(
                    "url"
                )

                if not url:
                    continue

                if url.startswith("//"):
                    url = (
                        "https:"
                        + url
                    )

                if url.startswith("http"):
                    images.append(
                        {
                            "url": url,
                            "width": thumbnail.get(
                                "width",
                                0,
                            ),
                            "height": thumbnail.get(
                                "height",
                                0,
                            ),
                        }
                    )

        for value in data.values():
            collect_images(
                value,
                images,
            )

    elif isinstance(data, list):

        for item in data:
            collect_images(
                item,
                images,
            )


def create_youtube_post_embed(post):
    text = post["text"]

    if len(text) > 3500:
        text = (
            text[:3497]
            + "..."
        )

    embed = discord.Embed(
        title="AION2 YouTube 새 게시글",
        description=text,
        url=post["url"],
        color=0xFF0000,
    )

    embed.set_author(
        name="📺 AION2 공식 YouTube"
    )

    if post.get("image"):
        embed.set_image(
            url=post["image"]
        )

    if post.get("published"):
        embed.add_field(
            name="🕐 게시",
            value=post["published"],
            inline=False,
        )

    embed.set_footer(
        text=(
            "AION2 HUB · "
            "공식 YouTube 게시글 알림"
        )
    )

    return embed


def create_youtube_post_button(post):
    view = discord.ui.View(
        timeout=None
    )

    view.add_item(
        discord.ui.Button(
            label="YouTube에서 보기",
            style=discord.ButtonStyle.link,
            url=post["url"],
            emoji="▶️",
        )
    )

    return view
