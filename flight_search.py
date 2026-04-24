import os
from datetime import datetime

import dotenv
import requests

dotenv.load_dotenv()


class FlightSearch:
    SEARCH_URL = "https://serpapi.com/search.json"

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.default_gl = os.getenv("SERPAPI_GL", "de")
        self.default_hl = os.getenv("SERPAPI_HL", "en")

    def search_flight(
        self,
        departure_date,
        origin,
        destination,
        adults=1,
        currency="EUR",
        travel_class="ECONOMY",
        stopage=False,
    ):
        if not self.api_key:
            print("Missing SERPAPI_API_KEY in environment.")
            return None

        params = {
            "engine": "google_flights",
            "api_key": self.api_key,
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date.strftime("%Y-%m-%d"),
            "type": "2",
            "adults": adults,
            "currency": currency,
            "travel_class": self._map_travel_class(travel_class),
            "sort_by": "2",
            "stops": "1" if stopage else "0",
            "gl": self.default_gl,
            "hl": self.default_hl,
        }

        try:
            response = requests.get(self.SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            offers = self._extract_offers(payload, currency)
            if offers:
                return {"data": offers}
            print(f"No flights found for {origin} -> {destination}.")
            return None
        except requests.exceptions.RequestException as error:
            print(f"An error occurred while searching flights: {error}")
            return None

    def _extract_offers(self, payload, currency):
        offers = []
        all_flights = payload.get("best_flights", []) + payload.get("other_flights", [])
        for raw_offer in all_flights:
            normalized = self._normalize_offer(raw_offer, currency)
            if normalized:
                offers.append(normalized)
        return offers

    def _normalize_offer(self, raw_offer, currency):
        flights = raw_offer.get("flights", [])
        if not flights:
            return None

        segments = []
        first_flight = flights[0]
        airline_name = first_flight.get("airline", "")
        for segment in flights:
            flight_number = str(segment.get("flight_number", ""))
            carrier_code, carrier_number = self._split_flight_number(flight_number, airline_name)
            segments.append(
                {
                    "departure": {
                        "iataCode": segment.get("departure_airport", {}).get("id", ""),
                        "at": self._format_time(segment.get("departure_airport", {}).get("time")),
                    },
                    "arrival": {
                        "iataCode": segment.get("arrival_airport", {}).get("id", ""),
                        "at": self._format_time(segment.get("arrival_airport", {}).get("time")),
                    },
                    "carrierCode": carrier_code,
                    "carrierName": segment.get("airline", airline_name),
                    "number": carrier_number,
                    "duration": self._duration_to_iso(segment.get("duration")),
                }
            )

        return {
            "price": {
                "total": str(raw_offer.get("price", "")),
                "currency": currency,
            },
            "itineraries": [
                {
                    "duration": self._duration_to_iso(raw_offer.get("total_duration")),
                    "segments": segments,
                }
            ],
        }

    def _map_travel_class(self, travel_class):
        mapping = {
            "ECONOMY": "1",
            "PREMIUM_ECONOMY": "2",
            "BUSINESS": "3",
            "FIRST": "4",
        }
        return mapping.get(str(travel_class).upper(), "1")

    def _split_flight_number(self, flight_number, airline_name):
        parts = flight_number.split()
        if len(parts) >= 2:
            return parts[0], parts[-1]
        if flight_number:
            return airline_name or "N/A", flight_number
        return airline_name or "N/A", "N/A"

    def _format_time(self, value):
        if not value:
            return ""
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p"):
            try:
                return datetime.strptime(value, fmt).isoformat()
            except ValueError:
                continue
        return value

    def _duration_to_iso(self, minutes):
        if minutes in (None, ""):
            return ""
        hours, mins = divmod(int(minutes), 60)
        return f"PT{hours}H{mins}M"
