import json
import os

import dotenv
import requests

dotenv.load_dotenv()


class DataManager:
    def __init__(self):
        self.sheety_end = os.getenv("SHEETY_PRICES_ENDPOINT", "")
        self.sheet = self.my_sheet()

    def my_sheet(self):
        if self.sheety_end:
            try:
                response = requests.get(url=self.sheety_end, timeout=30)
                response.raise_for_status()
                payload = response.json()
                if "prices" in payload:
                    return payload["prices"]
                print("Sheety response did not contain a 'prices' field, falling back to WATCH_ROUTES_JSON.")
            except requests.exceptions.RequestException as error:
                print(f"Sheety request failed: {error}. Falling back to WATCH_ROUTES_JSON.")

        fallback = os.getenv("WATCH_ROUTES_JSON", "")
        if fallback:
            try:
                routes = json.loads(fallback)
                if isinstance(routes, list):
                    return routes
                print("WATCH_ROUTES_JSON must be a JSON list of route objects.")
            except json.JSONDecodeError as error:
                print(f"Could not parse WATCH_ROUTES_JSON: {error}")

        print("No route data configured. Set SHEETY_PRICES_ENDPOINT or WATCH_ROUTES_JSON.")
        return []

    def routes(self):
        return [
            route
            for route in self.sheet
            if "iataCode" in route and "lowestPrice" in route
        ]

    def get_city_codes(self):
        return [city["iataCode"] for city in self.routes()]

    def cities(self):
        return self.get_city_codes()

    def get_prices(self):
        return [price["lowestPrice"] for price in self.routes()]

    def flight_price(self):
        return self.get_prices()
