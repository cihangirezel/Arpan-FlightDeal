import datetime
import os

import dotenv

from data_manager import DataManager
from flight_data import FlightData
from flight_search import FlightSearch
from notification_manager import NotificationManager

dotenv.load_dotenv()


def scan_deals(send_notifications=False):
    flight = FlightSearch()
    data_manager = DataManager()
    city_codes = data_manager.cities()
    target_prices = data_manager.flight_price()
    notifier = NotificationManager()

    origin = os.getenv("ORIGIN_IATA", "DUS")
    departure_date = datetime.datetime.strptime(
        os.getenv("DEPARTURE_DATE", "2026-06-15"),
        "%Y-%m-%d",
    )

    if not city_codes:
        print("No destinations configured. Add SHEETY_PRICES_ENDPOINT or WATCH_ROUTES_JSON to continue.")
        return []

    deals = []
    for destination, target_price in zip(city_codes, target_prices):
        flight_offers = flight.search_flight(
            origin=origin,
            departure_date=departure_date,
            destination=destination,
            currency=os.getenv("CURRENCY", "EUR"),
            travel_class=os.getenv("TRAVEL_CLASS", "ECONOMY"),
        )

        if not flight_offers:
            continue

        first_offer = flight_offers["data"][0]
        live_flight_info = FlightData(flight_offer=first_offer)

        if float(live_flight_info.flight_current_price()) < float(target_price):
            print(f"flight from {origin} to {destination}: {live_flight_info}")
            deals.append(live_flight_info)
            if send_notifications:
                notifier.notify(live_flight_info)
        else:
            print(f"No cheaper flight found for {destination}")

    return deals


def main():
    send_notifications = os.getenv("SEND_NOTIFICATIONS", "false").lower() == "true"
    deals = scan_deals(send_notifications=send_notifications)
    if not deals:
        print("No cheaper flight deals found.")


if __name__ == "__main__":
    main()
