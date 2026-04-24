import os
import smtplib

import dotenv
import requests

dotenv.load_dotenv()


class NotificationManager:
    def __init__(self):
        self.my_email = os.getenv("SMTP_EMAIL", "")
        self.my_pass = os.getenv("SMTP_PASSWORD", "")
        self.notify_to = os.getenv("NOTIFY_TO", self.my_email)
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    def send_email(self, message):
        if not self.my_email or not self.my_pass or not self.notify_to:
            print("Skipping email notification because SMTP settings are missing.")
            return

        subject = "Cheaper Flight Deal Available!"

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                connection.starttls()
                connection.login(user=self.my_email, password=self.my_pass)
                email_message = f"Subject: {subject}\n\n{message}"
                connection.sendmail(
                    from_addr=self.my_email,
                    to_addrs=self.notify_to,
                    msg=email_message,
                )
                print("Email sent successfully.")
        except Exception as error:
            print(f"Error occurred while sending email: {error}")

    def send_telegram(self, message, chat_id=None):
        if not self.telegram_bot_token:
            print("Skipping Telegram notification because TELEGRAM_BOT_TOKEN is missing.")
            return False

        target_chat_id = chat_id or self.telegram_chat_id
        if not target_chat_id:
            print("Skipping Telegram notification because TELEGRAM_CHAT_ID is missing.")
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            print("Telegram message sent successfully.")
            return True
        except requests.exceptions.RequestException as error:
            print(f"Error occurred while sending Telegram message: {error}")
            return False

    def notify(self, flight_data):
        message = f"Cheaper flight deal available: {flight_data}"
        self.send_email(message)
        self.send_telegram(message)
