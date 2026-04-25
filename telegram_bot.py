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
    "AYT 28.07.2026 03.08.2026 - round-trip search\n"
    "/help - show commands"
)

QUICK_SEARCH_PATTERN = re.compile(
    r"^/?(?:search\s+)?(?P<destination>[A-Za-z]{3})\s+"
    r"(?P<departure_date>\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})"
    r"(?:\s+(?P<return_date>\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}))?$",
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
            destination, departure_date, return_date = quick_search
            search_text = f"Searching DUS to {destination} on {departure_date.strftime('%Y-%m-%d')}"
            if return_date:
                search_text += f", returning {return_date.strftime('%Y-%m-%d')}"
            self.notifier.send_telegram(f"{search_text}...", chat_id=chat_id)
            self.notifier.send_telegram(
                self.search_destination(destination, departure_date, return_date),
                chat_id=chat_id,
            )
            return

        self.notifier.send_telegram(HELP_TEXT, chat_id=chat_id)

    def parse_quick_search(self, text):
        match = QUICK_SEARCH_PATTERN.match(text)
        if not match:
            return None

        destination = match.group("destination").upper()
        departure_date = self.parse_date(match.group("departure_date"))
        return_date = self.parse_date(match.group("return_date")) if match.group("return_date") else None
        if return_date and return_date <= departure_date:
            return None
        return destination, departure_date, return_date

    def parse_date(self, date_text):
        for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_text, date_format)
            except ValueError:
                continue
        raise ValueError(f"Invalid date: {date_text}")

    def search_destination(self, destination, departure_date, return_date=None):
        origin = os.getenv("ORIGIN_IATA", "DUS")
        currency = os.getenv("CURRENCY", "EUR")
        travel_class = os.getenv("TRAVEL_CLASS", "ECONOMY")

        flight_offers = FlightSearch().search_flight(
            origin=origin,
            departure_date=departure_date,
            destination=destination,
            return_date=return_date,
            currency=currency,
            travel_class=travel_class,
        )
        if not flight_offers:
            return self.format_no_result(origin, destination, departure_date, return_date)

        deal = FlightData(flight_offer=flight_offers["data"][0])
        if return_date:
            return self.format_round_trip_result(origin, destination, departure_date, return_date, deal)
        return self.format_one_way_result(origin, destination, departure_date, deal)

    def format_one_way_result(self, origin, destination, departure_date, deal):
        first_segment = deal.segments[0]
        return "\n".join(
            [
                self.format_segment(first_segment),
                f"PRICE: {self.format_price(deal)}",
            ]
        )

    def format_round_trip_result(self, origin, destination, departure_date, return_date, deal):
        outbound_segment = deal.segments[0]
        return_segment = deal.return_segments[0] if deal.return_segments else None
        lines = [self.format_segment(outbound_segment)]
        if return_segment:
            lines.append(self.format_segment(return_segment))
        lines.append(f"PRICE: {self.format_price(deal)}")
        return "\n".join(lines)

    def format_segment(self, segment):
        departure_time = self.format_local_datetime(segment["departure_time"])
        duration = self.format_duration(segment.get("duration", ""))
        return (
            f"Departure: from {segment['departure_airport']} to {segment['arrival_airport']} "
            f"at {departure_time}  Duration: {duration}"
        )

    def format_local_datetime(self, value):
        if not value:
            return "unknown time"
        for date_format in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(value, date_format)
                return parsed.strftime("%d-%m-%Y at %H:%M")
            except ValueError:
                continue
        return value

    def format_duration(self, value):
        match = re.match(r"^PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?$", value or "")
        if not match:
            return value or "unknown"
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        parts = []
        if hours:
            parts.append(f"{hours} Hour" + ("" if hours == 1 else "s"))
        if minutes:
            parts.append(f"{minutes} Minute" + ("" if minutes == 1 else "s"))
        return " ".join(parts) or "0 Minutes"

    def format_price(self, deal):
        currency = "Euro" if deal.currency == "EUR" else deal.currency
        return f"{deal.price} {currency}"

    def format_search_title(self, origin, destination, departure_date, return_date=None):
        title = f"Best result for {origin} to {destination} on {departure_date.strftime('%Y-%m-%d')}"
        if return_date:
            title += f", returning {return_date.strftime('%Y-%m-%d')}"
        return title

    def format_no_result(self, origin, destination, departure_date, return_date=None):
        title = f"No flights found for {origin} to {destination} on {departure_date.strftime('%Y-%m-%d')}"
        if return_date:
            title += f", returning {return_date.strftime('%Y-%m-%d')}"
        return f"{title}."

    def format_deals(self, deals):
        if not deals:
            return "No cheaper flight deals found right now."

        lines = ["Cheaper flight deals found:"]
        for deal in deals:
            lines.append(f"- {deal}")
        return "\n".join(lines)


if __name__ == "__main__":
    TelegramBot().run()
