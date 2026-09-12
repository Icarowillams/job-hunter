import smtplib
from email.message import EmailMessage


class SMTPClient:
    """SMTP adapter responsible for delivering email messages."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    def send_message(self, message: EmailMessage) -> None:
        with smtplib.SMTP(
            self.host,
            self.port,
            timeout=self.timeout,
        ) as smtp:
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.send_message(message)
