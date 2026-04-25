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
3. Fill in your SerpApi key, optional Aviationstack key, origin, departure date, and optional SMTP credentials.
4. Either set a working `SHEETY_PRICES_ENDPOINT` or provide routes directly via `WATCH_ROUTES_JSON`.
5. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

```ini
SERPAPI_API_KEY=your_serpapi_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
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
docker build -t cihangir-flightdeal .
```

Run it with your environment file:

```bash
docker run --rm --env-file .env cihangir-flightdeal
```

Start the Telegram bot:

```bash
docker run --rm --env-file .env cihangir-flightdeal python telegram_bot.py
```

## Telegram

Create a bot with Telegram's `@BotFather`, put the token in `TELEGRAM_BOT_TOKEN`, and set `TELEGRAM_CHAT_ID` to your Telegram chat id.

Supported commands:

- `/deals`: scan the configured routes and reply with the cheapest deals below your thresholds.
- `/scan`: same as `/deals`.
- `/search Antalya 28.09.2026`: search one destination and date.
- `Antalya 28.09.2026`: quick search one destination and date.
- `Antalya 28.07.2026 03.08.2026`: round-trip search with outbound and return dates.
- `London 15.06-18.06`: round-trip shorthand with day and month only.
- `/help`: show the available commands.

The bot understands a broad set of major European city names and resolves them to their flight search codes behind the scenes.

Set `SEND_NOTIFICATIONS=true` if you also want `python main.py` to push deal alerts to email and Telegram during a normal scheduled scan.

## Different Dates

Each route can include its own `departureDate`:

```ini
WATCH_ROUTES_JSON=[{"cityName":"Antalya","lowestPrice":150,"departureDate":"2026-06-15"},{"cityName":"Lisbon","lowestPrice":160,"departureDate":"2026-07-03"}]
```

If a route does not include `departureDate`, the app uses the global `DEPARTURE_DATE` value.

Route entries can use `cityName`, `destination`, or `iataCode`. The app will use whichever one is present, then resolve major city names like `Antalya`, `London`, `Paris`, or `Barcelona` to the right search code.

## Notes

- This version uses SerpApi's `google_flights` engine with one-way searches.
- The app normalizes SerpApi responses so the rest of the code can keep its simpler flight parsing flow.
- If SerpApi fails, Aviationstack is used as a fallback for schedule data only. It does not provide fare prices, so price-based deal checks are skipped for those fallback results.
- If SMTP values are missing, the script will still run and print deals without trying to send email.
- `WATCH_ROUTES_JSON` is the easiest way to test locally or in Docker when you do not want to depend on a live Sheety sheet.
