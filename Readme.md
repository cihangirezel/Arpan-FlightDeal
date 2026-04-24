# Flight Deal Finder

Flight Deal Finder compares live ticket prices from the SerpApi Google Flights API against your target thresholds stored in a Google Sheet via Sheety, then alerts you by email when it finds a cheaper trip.

## Features

- Searches live flights with SerpApi instead of Amadeus.
- Compares live prices against your saved target prices.
- Reads destination IATA codes and price thresholds from Sheety.
- Can send email alerts through Gmail SMTP.

## Setup

1. Create a SerpApi account and get your API key from [serpapi.com](https://serpapi.com/).
2. Create a `.env` file by copying `.env.example`.
3. Fill in your SerpApi key, origin, departure date, and optional SMTP credentials.
4. Update `data_manager.py` with your Sheety endpoint.
5. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

```ini
SERPAPI_API_KEY=your_serpapi_key
SERPAPI_GL=de
SERPAPI_HL=en
ORIGIN_IATA=DUS
DEPARTURE_DATE=2026-06-15
CURRENCY=EUR
TRAVEL_CLASS=ECONOMY
SMTP_EMAIL=you@example.com
SMTP_PASSWORD=your_app_password
NOTIFY_TO=you@example.com
```

## Run

```bash
python main.py
```

## Notes

- This version uses SerpApi's `google_flights` engine with one-way searches.
- The app normalizes SerpApi responses so the rest of the code can keep its simpler flight parsing flow.
- If SMTP values are missing, the script will still run and print deals without trying to send email.
