import os
import smtplib

import dotenv

dotenv.load_dotenv()


class NotificationManager:
    def __init__(self):
        self.my_email = os.getenv("SMTP_EMAIL", "")
        self.my_pass = os.getenv("SMTP_PASSWORD", "")
        self.notify_to = os.getenv("NOTIFY_TO", self.my_email)

    def send_email(self, flight_data):
        if not self.my_email or not self.my_pass or not self.notify_to:
            print("Skipping email notification because SMTP settings are missing.")
            return

        subject = "Cheaper Flight Deal Available!"
        message = f"Cheaper flight deal available: {flight_data}"

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

    def notify(self, flight_data):
        self.send_email(flight_data)
