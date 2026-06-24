import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    STOCK_WATCHLIST: List[str]
    SCHEDULE_TIMES: List[str]

    def __init__(self):
        self.GEMINI_API_KEY = self._get_required_env("GEMINI_API_KEY")
        self.TELEGRAM_BOT_TOKEN = self._get_required_env("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = self._get_required_env("TELEGRAM_CHAT_ID")
        
        self.STOCK_WATCHLIST = self._parse_list(self._get_required_env("STOCK_WATCHLIST"))
        self.SCHEDULE_TIMES = self._parse_list(self._get_required_env("SCHEDULE_TIMES"))

    def _get_required_env(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(f"Missing required environment variable: {key}")
        return value

    def _parse_list(self, value: str) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]

settings = Settings()
