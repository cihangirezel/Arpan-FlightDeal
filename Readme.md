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
4. Either set a working `SHEETY_PRICES_ENDPOINT` or provide routes directly via `WATCH_ROUTES_JSON`.
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
SHEETY_PRICES_ENDPOINT=
WATCH_ROUTES_JSON=[{"iataCode":"AYT","lowestPrice":150,"departureDate":"2026-06-15"},{"iataCode":"LIS","lowestPrice":160,"departureDate":"2026-07-03"}]
SMTP_EMAIL=you@example.com
SMTP_PASSWORD=your_app_password
NOTIFY_TO=you@example.com
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
TELEGRAM_POLL_INTERVAL=5
```

## Run

```bash
python main.py
```

## Docker

Build the image:

```bash
docker build -t arpan-flightdeal .
```

Run it with your environment file:

```bash
docker run --rm --env-file .env arpan-flightdeal
```

Start the Telegram bot:

```bash
docker run --rm --env-file .env arpan-flightdeal python telegram_bot.py
```

## Telegram

Create a bot with Telegram's `@BotFather`, put the token in `TELEGRAM_BOT_TOKEN`, and set `TELEGRAM_CHAT_ID` to your Telegram chat id.

Supported commands:

- `/deals`: scan the configured routes and reply with the cheapest deals below your thresholds.
- `/scan`: same as `/deals`.
- `/search AYT 28.09.2026`: search one destination and date.
- `AYT 28.09.2026`: quick search one destination and date.
- `/help`: show the available commands.

Set `SEND_NOTIFICATIONS=true` if you also want `python main.py` to push deal alerts to email and Telegram during a normal scheduled scan.

## Different Dates

Each route can include its own `departureDate`:

```ini
WATCH_ROUTES_JSON=[{"iataCode":"AYT","lowestPrice":150,"departureDate":"2026-06-15"},{"iataCode":"LIS","lowestPrice":160,"departureDate":"2026-07-03"}]
```

If a route does not include `departureDate`, the app uses the global `DEPARTURE_DATE` value.

## Notes

- This version uses SerpApi's `google_flights` engine with one-way searches.
- The app normalizes SerpApi responses so the rest of the code can keep its simpler flight parsing flow.
- If SMTP values are missing, the script will still run and print deals without trying to send email.
- `WATCH_ROUTES_JSON` is the easiest way to test locally or in Docker when you do not want to depend on a live Sheety sheet.
