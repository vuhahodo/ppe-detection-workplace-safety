from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


class TelegramNotifier:
    def __init__(self, config: dict):
        load_dotenv()
        self.config = config
        telegram_cfg = config.get("telegram", {})
        self.enabled = bool(telegram_cfg.get("enabled", True))
        self.token = os.getenv(telegram_cfg.get("bot_token_env", "TELEGRAM_BOT_TOKEN"), "")
        self.chat_id = os.getenv(telegram_cfg.get("chat_id_env", "TELEGRAM_CHAT_ID"), "")
        self.thread_id = os.getenv(telegram_cfg.get("message_thread_id_env", "TELEGRAM_MESSAGE_THREAD_ID"), "")
        self.retry_count = int(telegram_cfg.get("retry_count", 1))

    def send_violation_alert(self, caption: str, raw_image_path: str, annotated_image_path: str) -> tuple[bool, str | None]:
        if not self.enabled:
            return False, "Telegram disabled"
        if not self.token or not self.chat_id:
            return False, "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"
        try:
            for attempt in range(self.retry_count + 1):
                ok, error = self._send_once(caption, raw_image_path, annotated_image_path)
                if ok:
                    return True, None
                if attempt == self.retry_count:
                    return False, error
        except Exception as exc:
            return False, str(exc)
        return False, "Unknown Telegram error"

    def _send_once(self, caption: str, raw_image_path: str, annotated_image_path: str) -> tuple[bool, str | None]:
        base = f"https://api.telegram.org/bot{self.token}"
        data = {"chat_id": self.chat_id, "text": caption}
        if self.thread_id:
            data["message_thread_id"] = self.thread_id
        resp = requests.post(f"{base}/sendMessage", data=data, timeout=20)
        if not resp.ok:
            return False, resp.text
        for image_path in (raw_image_path, annotated_image_path):
            with Path(image_path).open("rb") as f:
                photo_data = {"chat_id": self.chat_id}
                if self.thread_id:
                    photo_data["message_thread_id"] = self.thread_id
                photo_resp = requests.post(f"{base}/sendPhoto", data=photo_data, files={"photo": f}, timeout=30)
            if not photo_resp.ok:
                return False, photo_resp.text
        return True, None
