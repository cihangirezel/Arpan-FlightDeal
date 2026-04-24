import os
import re
import time
from datetime import datetime

import dotenv
import requests

from flight_data import FlightData
from flight_search import FlightSearch
from main import scan_deals
from notification_manager import NotificationManager

dotenv.load_dotenv()


HELP_TEXT = (
    "Travel deal bot commands:\n"
    "/deals - scan configured routes now\n"
    "/search AYT 28.09.2026 - search one destination and date\n"
    "AYT 28.09.2026 - quick search one destination and date\n"
    "/help - show commands"
)

QUICK_SEARCH_PATTERN = re.compile(
    r"^/?(?:search\s+)?(?P<destination>[A-Za-z]{3})\s+(?P<date>\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
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

        quick_search = self.parse_quick_search(text)
        if quick_search:
            destination, departure_date = quick_search
            self.notifier.send_telegram(
                f"Searching DUS to {destination} on {departure_date.strftime('%Y-%m-%d')}...",
                chat_id=chat_id,
            )
            self.notifier.send_telegram(
                self.search_destination(destination, departure_date),
                chat_id=chat_id,
            )
            return

        self.notifier.send_telegram(HELP_TEXT, chat_id=chat_id)

    def parse_quick_search(self, text):
        match = QUICK_SEARCH_PATTERN.match(text)
        if not match:
            return None

        destination = match.group("destination").upper()
        date_text = match.group("date")
        for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return destination, datetime.strptime(date_text, date_format)
            except ValueError:
                continue
        return None

    def search_destination(self, destination, departure_date):
        origin = os.getenv("ORIGIN_IATA", "DUS")
        currency = os.getenv("CURRENCY", "EUR")
        travel_class = os.getenv("TRAVEL_CLASS", "ECONOMY")

        flight_offers = FlightSearch().search_flight(
            origin=origin,
            departure_date=departure_date,
            destination=destination,
            currency=currency,
            travel_class=travel_class,
        )
        if not flight_offers:
            return f"No flights found for {origin} to {destination} on {departure_date.strftime('%Y-%m-%d')}."

        deal = FlightData(flight_offer=flight_offers["data"][0])
        return f"Best result for {origin} to {destination} on {departure_date.strftime('%Y-%m-%d')}:\n{deal}"

    def format_deals(self, deals):
        if not deals:
            return "No cheaper flight deals found right now."

        lines = ["Cheaper flight deals found:"]
        for deal in deals:
            lines.append(f"- {deal}")
        return "\n".join(lines)


if __name__ == "__main__":
    TelegramBot().run()
