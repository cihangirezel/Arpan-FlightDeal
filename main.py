from flight_search import FlightSearch
from flight_data import FlightData
from data_manager import DataManager
from notification_manager import NotificationManager
import datetime
import os

import dotenv

dotenv.load_dotenv()

flight = FlightSearch()
data_manager = DataManager()
city_codes = data_manager.cities()
my_price = data_manager.flight_price()
email_notification = NotificationManager()

origin = os.getenv("ORIGIN_IATA", "DUS")
departure_date = datetime.datetime.strptime(
    os.getenv("DEPARTURE_DATE", "2026-06-15"),
    "%Y-%m-%d",
)


for destination in city_codes:
    flight_offers = flight.search_flight(
        origin=origin,
        departure_date=departure_date,
        destination=destination,
        currency=os.getenv("CURRENCY", "EUR"),
        travel_class=os.getenv("TRAVEL_CLASS", "ECONOMY"),
    )

    if flight_offers:
        for offer in flight_offers["data"]:
            live_flight_info = FlightData(flight_offer = offer)

            if float(live_flight_info.flight_current_price()) < float(my_price[city_codes.index(destination)]):
                print(f"flight from {origin} to {destination}: {live_flight_info}")
                # Uncomment this after you configure SMTP settings.
                # email_notification.notify(live_flight_info)
                
            else:
                print(f"No cheaper flight found for {destination}")

            break





