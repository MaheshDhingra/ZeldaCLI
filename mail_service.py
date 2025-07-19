import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

class MailService:
    def __init__(self, smtp_server, smtp_port, smtp_username, smtp_password, sender_email):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.inbox = [] # Still simulated for receiving, as a full IMAP/POP3 client is out of scope
        self.sent_items = []
        self.current_user = sender_email # Use the actual sender email as the current user

    def send_message(self, recipient, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls() # Secure the connection
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            message = {
                "from": self.sender_email,
                "to": recipient,
                "subject": subject,
                "body": body,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.sent_items.append(message)
            return "Message sent successfully!"
        except Exception as e:
            return f"Failed to send message: {e}"

    def get_inbox(self):
        return self.inbox

    def get_sent_items(self):
        return self.sent_items

    def clear_inbox(self):
        self.inbox = []
        return "Inbox cleared."

    def clear_sent_items(self):
        self.sent_items = []
        return "Sent items cleared."
