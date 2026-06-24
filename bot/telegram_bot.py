import logging
import re
import time
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)

class TelegramReporter:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _chunk_text(self, text: str, limit: int = 4000) -> list[str]:
        """Chia tin nhắn thành các phần nhỏ hơn limit theo dòng."""
        if len(text) <= limit:
            return [text]

        chunks = []
        lines = text.split("\n")
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > limit:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    chunks.append(line[:limit])
                    current_chunk = line[limit:]
            else:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def send_report(self, message: str) -> bool:
        """
        Gửi báo cáo qua Telegram API.
        Hỗ trợ Message Chunking và Fallback Plain-text.
        """
        chunks = self._chunk_text(message)
        all_success = True

        for chunk in chunks:
            success = self._send_with_retry(chunk)
            if not success:
                all_success = False

        return all_success

    def _send_with_retry(self, text: str, max_retries: int = 3) -> bool:
        """Thực hiện gửi một đoạn tin nhắn với cơ chế retry và fallback"""
        for attempt in range(max_retries):
            try:
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                }
                response = requests.post(self.base_url, data=payload, timeout=10)

                if response.status_code == 200:
                    return True

                resp_data = response.json()
                description = resp_data.get("description", "")

                if "can't parse entities" in description.lower() or "parse" in description.lower():
                    logger.warning("Telegram parse error, falling back to plain-text.")
                    return self._send_plain_text(text)

                if response.status_code == 429:
                    retry_after = resp_data.get("parameters", {}).get("retry_after", 5)
                    logger.warning(f"Rate limited. Retrying after {retry_after}s.")
                    time.sleep(retry_after)
                    continue

                logger.error(f"Telegram API Error {response.status_code}: {description}")

            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")

            if attempt < max_retries - 1:
                time.sleep(2)

        return False

    def _send_plain_text(self, text: str) -> bool:
        """Gửi text thuần túy khi bị lỗi parse HTML"""
        clean_text = re.sub(r'<[^>]+>', '', text)
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": clean_text,
                "parse_mode": None,
            }
            response = requests.post(self.base_url, data=payload, timeout=10)
            if response.status_code == 200:
                return True
            logger.error(f"Plain text fallback failed: {response.text}")
        except requests.RequestException as e:
            logger.error(f"Plain text request failed: {e}")
        return False
