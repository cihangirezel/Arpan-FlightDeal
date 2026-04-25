import os
from datetime import datetime
from urllib.parse import quote_plus

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
        return_date=None,
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
            "type": "1" if return_date else "2",
            "adults": adults,
            "currency": currency,
            "travel_class": self._map_travel_class(travel_class),
            "sort_by": "2",
            "stops": "1" if stopage else "0",
            "gl": self.default_gl,
            "hl": self.default_hl,
        }
        if return_date:
            params["return_date"] = return_date.strftime("%Y-%m-%d")

        try:
            response = requests.get(self.SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if return_date:
                offers = self._extract_round_trip_offers(payload, params, currency)
                if offers:
                    return {"data": offers}
                print(f"No round-trip flights found for {origin} -> {destination}.")
                return None

            offers = self._extract_offers(payload, currency)
            if offers:
                return {"data": offers}
            print(f"No flights found for {origin} -> {destination}.")
            return None
        except requests.exceptions.RequestException as error:
            print(f"An error occurred while searching flights: {error}")
            return None

    def _extract_round_trip_offers(self, payload, params, currency):
        outbound_options = payload.get("best_flights", []) + payload.get("other_flights", [])
        if not outbound_options:
            return []

        outbound_offer = outbound_options[0]
        departure_token = outbound_offer.get("departure_token")
        if not departure_token:
            return []

        return_params = dict(params)
        return_params["departure_token"] = departure_token
        try:
            response = requests.get(self.SEARCH_URL, params=return_params, timeout=30)
            response.raise_for_status()
            return_payload = response.json()
        except requests.exceptions.RequestException as error:
            print(f"An error occurred while searching return flights: {error}")
            return []

        return_options = return_payload.get("best_flights", []) + return_payload.get("other_flights", [])
        if not return_options:
            return []

        return_offer = return_options[0]
        booking_details = self._fetch_booking_details(return_offer.get("booking_token"), params)
        booking_link = self._google_flights_link(params)
        return [self._normalize_round_trip_offer(outbound_offer, return_offer, currency, booking_details, booking_link)]

    def _extract_offers(self, payload, currency):
        offers = []
        all_flights = payload.get("best_flights", []) + payload.get("other_flights", [])
        for raw_offer in all_flights:
            normalized = self._normalize_offer(raw_offer, currency)
            if normalized:
                offers.append(normalized)
        return offers

    def _normalize_offer(self, raw_offer, currency):
        itinerary = self._normalize_itinerary(raw_offer)
        if not itinerary:
            return None

        booking_link = self._google_flights_link_from_offer(raw_offer)
        return {
            "price": {
                "total": str(raw_offer.get("price", "")),
                "currency": currency,
            },
            "itineraries": [itinerary],
            "booking": {
                "book_with": self._airline_summary([itinerary]),
                "link": booking_link,
            },
        }

    def _normalize_round_trip_offer(self, outbound_offer, return_offer, currency, booking_details, booking_link):
        outbound_itinerary = self._normalize_itinerary(outbound_offer)
        return_itinerary = self._normalize_itinerary(return_offer)
        if not outbound_itinerary or not return_itinerary:
            return None

        return {
            "price": {
                "total": str(return_offer.get("price") or outbound_offer.get("price", "")),
                "currency": currency,
            },
            "itineraries": [outbound_itinerary, return_itinerary],
            "booking": {
                "book_with": booking_details.get("book_with") or self._airline_summary([outbound_itinerary, return_itinerary]),
                "link": booking_details.get("link") or booking_link,
            },
        }

    def _normalize_itinerary(self, raw_offer):
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
            "duration": self._duration_to_iso(raw_offer.get("total_duration")),
            "segments": segments,
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

    def _fetch_booking_details(self, booking_token, params):
        if not booking_token:
            return {}

        booking_params = dict(params)
        booking_params.pop("departure_token", None)
        booking_params["booking_token"] = booking_token
        try:
            response = requests.get(self.SEARCH_URL, params=booking_params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as error:
            print(f"An error occurred while fetching booking options: {error}")
            return {}

        options = payload.get("booking_options", [])
        if not options:
            return {}

        option = options[0]
        together = option.get("together") or {}
        book_with = together.get("book_with")
        booking_request = together.get("booking_request") or {}
        link = booking_request.get("url") if not booking_request.get("post_data") else ""
        return {
            "book_with": book_with,
            "link": link,
        }

    def _google_flights_link(self, params):
        origin = params.get("departure_id", "")
        destination = params.get("arrival_id", "")
        outbound_date = params.get("outbound_date", "")
        return_date = params.get("return_date", "")
        query = f"Flights from {origin} to {destination} on {outbound_date}"
        if return_date:
            query += f" returning {return_date}"
        return "https://www.google.com/travel/flights?q=" + quote_plus(query)

    def _google_flights_link_from_offer(self, raw_offer):
        flights = raw_offer.get("flights", [])
        if not flights:
            return ""
        first_flight = flights[0]
        origin = first_flight.get("departure_airport", {}).get("id", "")
        destination = flights[-1].get("arrival_airport", {}).get("id", "")
        outbound_time = first_flight.get("departure_airport", {}).get("time", "")
        outbound_date = outbound_time.split(" ")[0] if outbound_time else ""
        query = f"Flights from {origin} to {destination} on {outbound_date}"
        return "https://www.google.com/travel/flights?q=" + quote_plus(query)

    def _airline_summary(self, itineraries):
        airlines = []
        for itinerary in itineraries:
            for segment in itinerary.get("segments", []):
                carrier_name = segment.get("carrierName")
                if carrier_name and carrier_name not in airlines:
                    airlines.append(carrier_name)
        return ", ".join(airlines)
