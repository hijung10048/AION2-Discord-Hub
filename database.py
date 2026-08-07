import sqlite3


DB_PATH = "aion2hub.db"

CHANNEL_COLUMNS = {
    "coupon_channel_id",
    "notice_channel_id",
    "update_channel_id",
    "youtube_channel_id",
    "maintenance_channel_id",
}

KNOWN_COUPON_BASELINE_ID = "6a2546841846ff309ba4613f"


def _connect():
    return sqlite3.connect(DB_PATH)


def _ensure_column(
    cursor,
    table_name: str,
    column_name: str,
    column_type: str,
):
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )
    existing = {
        row[1]
        for row in cursor.fetchall()
    }

    if column_name not in existing:
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_type}
            """
        )


def init_db():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            coupon_channel_id INTEGER,
            notice_channel_id INTEGER,
            update_channel_id INTEGER,
            youtube_channel_id INTEGER,
            maintenance_channel_id INTEGER
        )
    """)

    # 기존 DB를 그대로 사용하는 경우 점검 채널 컬럼만 안전하게 추가
    _ensure_column(
        cursor,
        "guild_settings",
        "maintenance_channel_id",
        "INTEGER",
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS youtube_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_video_id TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO youtube_state (
            id,
            last_video_id
        )
        VALUES (1, NULL)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS youtube_deliveries (
            guild_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, video_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notice_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_article_id TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO notice_state (
            id,
            last_article_id
        )
        VALUES (1, NULL)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notice_deliveries (
            guild_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, article_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_deliveries (
            guild_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, article_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS update_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_article_id TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO update_state (
            id,
            last_article_id
        )
        VALUES (1, NULL)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS update_deliveries (
            guild_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, article_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_article_id TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO coupon_state (
            id,
            last_article_id
        )
        VALUES (1, ?)
    """, (KNOWN_COUPON_BASELINE_ID,))
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon_deliveries (
            guild_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, article_id)
        )
    """)

    conn.commit()
    conn.close()


# 기존 호출 호환용
def init_notice_state():
    init_db()


def init_update_state():
    init_db()


def init_coupon_state():
    init_db()


def set_channel(
    guild_id: int,
    column_name: str,
    channel_id: int,
):
    if column_name not in CHANNEL_COLUMNS:
        raise ValueError(
            "허용되지 않은 채널 설정입니다."
        )

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO guild_settings (
            guild_id
        )
        VALUES (?)
        """,
        (guild_id,),
    )

    cursor.execute(
        f"""
        UPDATE guild_settings
        SET {column_name} = ?
        WHERE guild_id = ?
        """,
        (channel_id, guild_id),
    )

    conn.commit()
    conn.close()


def get_settings(guild_id: int):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            guild_id,
            coupon_channel_id,
            notice_channel_id,
            update_channel_id,
            youtube_channel_id,
            maintenance_channel_id
        FROM guild_settings
        WHERE guild_id = ?
    """, (guild_id,))

    result = cursor.fetchone()
    conn.close()
    return result


def _get_channels(column_name: str):
    if column_name not in CHANNEL_COLUMNS:
        raise ValueError(
            "허용되지 않은 채널 설정입니다."
        )

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT guild_id, {column_name}
        FROM guild_settings
        WHERE {column_name} IS NOT NULL
        """
    )

    result = cursor.fetchall()
    conn.close()
    return result


def get_youtube_channels():
    return _get_channels(
        "youtube_channel_id"
    )


def get_notice_channels():
    return _get_channels(
        "notice_channel_id"
    )


def get_update_channels():
    return _get_channels(
        "update_channel_id"
    )


def get_coupon_channels():
    return _get_channels(
        "coupon_channel_id"
    )


def get_maintenance_channels():
    return _get_channels(
        "maintenance_channel_id"
    )


def _get_state(
    table_name: str,
    column_name: str,
):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT {column_name}
        FROM {table_name}
        WHERE id = 1
        """
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return row[0]


def _set_state(
    table_name: str,
    column_name: str,
    value: str,
):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE {table_name}
        SET {column_name} = ?
        WHERE id = 1
        """,
        (value,),
    )
    conn.commit()
    conn.close()


def get_last_youtube_video_id():
    return _get_state(
        "youtube_state",
        "last_video_id",
    )


def set_last_youtube_video_id(
    video_id: str,
):
    _set_state(
        "youtube_state",
        "last_video_id",
        video_id,
    )


def get_last_notice_id():
    return _get_state(
        "notice_state",
        "last_article_id",
    )


def set_last_notice_id(
    article_id: str,
):
    _set_state(
        "notice_state",
        "last_article_id",
        article_id,
    )


def get_last_update_id():
    return _get_state(
        "update_state",
        "last_article_id",
    )


def set_last_update_id(
    article_id: str,
):
    _set_state(
        "update_state",
        "last_article_id",
        article_id,
    )


def get_last_coupon_id():
    return _get_state(
        "coupon_state",
        "last_article_id",
    )


def set_last_coupon_id(
    article_id: str,
):
    _set_state(
        "coupon_state",
        "last_article_id",
        article_id,
    )


def _is_delivered(
    table_name: str,
    guild_id: int,
    item_column: str,
    item_id: str,
):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT 1
        FROM {table_name}
        WHERE guild_id = ?
          AND {item_column} = ?
        """,
        (guild_id, item_id),
    )

    result = cursor.fetchone()
    conn.close()
    return result is not None


def _save_delivery(
    table_name: str,
    guild_id: int,
    item_column: str,
    item_id: str,
):
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        INSERT OR IGNORE INTO {table_name} (
            guild_id,
            {item_column}
        )
        VALUES (?, ?)
        """,
        (guild_id, item_id),
    )

    conn.commit()
    conn.close()


def is_youtube_delivered(
    guild_id: int,
    video_id: str,
):
    return _is_delivered(
        "youtube_deliveries",
        guild_id,
        "video_id",
        video_id,
    )


def save_youtube_delivery(
    guild_id: int,
    video_id: str,
):
    _save_delivery(
        "youtube_deliveries",
        guild_id,
        "video_id",
        video_id,
    )


def is_notice_delivered(
    guild_id: int,
    article_id: str,
):
    return _is_delivered(
        "notice_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def save_notice_delivery(
    guild_id: int,
    article_id: str,
):
    _save_delivery(
        "notice_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def is_maintenance_delivered(
    guild_id: int,
    article_id: str,
):
    return _is_delivered(
        "maintenance_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def save_maintenance_delivery(
    guild_id: int,
    article_id: str,
):
    _save_delivery(
        "maintenance_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def is_update_delivered(
    guild_id: int,
    article_id: str,
):
    return _is_delivered(
        "update_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def save_update_delivery(
    guild_id: int,
    article_id: str,
):
    _save_delivery(
        "update_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def is_coupon_delivered(
    guild_id: int,
    article_id: str,
):
    return _is_delivered(
        "coupon_deliveries",
        guild_id,
        "article_id",
        article_id,
    )


def save_coupon_delivery(
    guild_id: int,
    article_id: str,
):
    _save_delivery(
        "coupon_deliveries",
        guild_id,
        "article_id",
        article_id,
    )
