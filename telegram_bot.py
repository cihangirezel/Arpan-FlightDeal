import os
import time

import dotenv
import requests

from main import scan_deals
from notification_manager import NotificationManager

dotenv.load_dotenv()


HELP_TEXT = (
    "Travel deal bot commands:\n"
    "/deals - scan configured routes now\n"
    "/help - show commands"
)


class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.poll_interval = int(os.getenv("TELEGRAM_POLL_INTERVAL", "5"))
        self.notifier = NotificationManager()
        self.offset = None

        if not self.bot_token:
            raise SystemExit("Missing TELEGRAM_BOT_TOKEN in environment.")

    def api_url(self, method):
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    def run(self):
        print("Telegram bot is running. Send /deals in Telegram to scan flights.")
        while True:
            for update in self.get_updates():
                self.handle_update(update)
            time.sleep(self.poll_interval)

    def get_updates(self):
        params = {"timeout": 30}
        if self.offset is not None:
            params["offset"] = self.offset

        try:
            response = requests.get(self.api_url("getUpdates"), params=params, timeout=35)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as error:
            print(f"Telegram polling failed: {error}")
            return []

        updates = payload.get("result", [])
        if updates:
            self.offset = updates[-1]["update_id"] + 1
        return updates

    def handle_update(self, update):
        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return

        if self.allowed_chat_id and chat_id != self.allowed_chat_id:
            self.notifier.send_telegram("This bot is configured for another chat.", chat_id=chat_id)
            return

        if text.startswith("/start") or text.startswith("/help"):
            self.notifier.send_telegram(HELP_TEXT, chat_id=chat_id)
            return

        if text.startswith("/deals") or text.startswith("/scan"):
            self.notifier.send_telegram("Scanning flight deals now...", chat_id=chat_id)
            deals = scan_deals(send_notifications=False)
            self.notifier.send_telegram(self.format_deals(deals), chat_id=chat_id)
            return

        self.notifier.send_telegram(HELP_TEXT, chat_id=chat_id)

    def format_deals(self, deals):
        if not deals:
            return "No cheaper flight deals found right now."

        lines = ["Cheaper flight deals found:"]
        for deal in deals:
            lines.append(f"- {deal}")
        return "\n".join(lines)


if __name__ == "__main__":
    TelegramBot().run()
