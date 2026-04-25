class FlightData:
    def __init__(self, flight_offer):
        self.itineraries = flight_offer["itineraries"]
        itinerary = self.itineraries[0]
        first_segment = itinerary["segments"][0]

        self.price = flight_offer["price"]["total"]
        self.currency = flight_offer["price"]["currency"]
        self.departure_airport = first_segment["departure"]["iataCode"]
        self.departure_time = first_segment["departure"]["at"]
        self.arrival_airport = itinerary["segments"][-1]["arrival"]["iataCode"]
        self.arrival_time = itinerary["segments"][-1]["arrival"]["at"]
        self.carrier_code = first_segment.get("carrierCode", "")
        self.carrier_name = first_segment.get("carrierName", self.carrier_code)
        self.carrier_numb = first_segment.get("number", "")
        self.duration = itinerary.get("duration", "")
        self.segments = self._segments_for_itinerary(itinerary)
        self.return_segments = (
            self._segments_for_itinerary(self.itineraries[1])
            if len(self.itineraries) > 1
            else []
        )

    def __str__(self):
        flight_number = f"{self.carrier_code}{self.carrier_numb}".strip()
        if not flight_number:
            flight_number = self.carrier_name
        return (
            f"Price: {self.price} {self.currency}, Departure: {self.departure_airport} at "
            f"{self.departure_time}, Arrival: {self.arrival_airport} at {self.arrival_time}, "
            f"Carrier: {flight_number}, Duration: {self.duration}"
        )

    def flight_current_price(self):
        return self.price

    def _segments_for_itinerary(self, itinerary):
        return [
            {
                "departure_airport": segment["departure"]["iataCode"],
                "departure_time": segment["departure"]["at"],
                "arrival_airport": segment["arrival"]["iataCode"],
                "arrival_time": segment["arrival"]["at"],
                "carrier_code": segment.get("carrierCode", ""),
                "carrier_name": segment.get("carrierName", ""),
                "carrier_numb": segment.get("number", ""),
                "duration": segment.get("duration", ""),
            }
            for segment in itinerary["segments"]
        ]
