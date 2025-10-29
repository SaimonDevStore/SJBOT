import os
from dataclasses import dataclass
from typing import List, Optional
from zoneinfo import ZoneInfo


def _get_env_list(name: str) -> List[int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    result: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


@dataclass
class Settings:
    tracking_id: str
    app_key: str
    app_secret: str
    bot_token: str
    channel_id: str
    timezone: ZoneInfo
    admin_ids: List[int]
    min_per_hour_default: int
    max_per_hour_default: int
    database_path: str
    log_dir: str

    @staticmethod
    def load() -> "Settings":
        tz_name = os.getenv("TIMEZONE", "America/Sao_Paulo")
        return Settings(
            tracking_id=os.getenv("TRACKING_ID", "BOT_TELEGRAM"),
            app_key=os.getenv("APP_KEY", ""),
            app_secret=os.getenv("APP_SECRET", ""),
            bot_token=os.getenv("BOT_TOKEN", ""),
            channel_id=os.getenv("CHANNEL_ID", "@SJPROMOS"),
            timezone=ZoneInfo(tz_name),
            admin_ids=_get_env_list("ADMIN_IDS"),
            min_per_hour_default=int(os.getenv("MIN_PER_HOUR", "20")),
            max_per_hour_default=int(os.getenv("MAX_PER_HOUR", "25")),
            database_path=os.getenv("DATABASE_PATH", "data/bot.sqlite3"),
            log_dir=os.getenv("LOG_DIR", "logs"),
        )


