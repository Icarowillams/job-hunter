from email.message import EmailMessage

import pytest

from src.infrastructure.smtp_client import SMTPClient


class FakeSMTPConnection:
    def __init__(self):
        self.calls = []

    def starttls(self):
        self.calls.append(("starttls",))

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, message):
        self.calls.append(("send_message", message))

    def quit(self):
        self.calls.append(("quit",))


def test_smtp_client_sends_message_using_tls(monkeypatch):
    connection = FakeSMTPConnection()

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            connection.calls.append(
                ("connect", host, port, timeout)
            )

        def __enter__(self):
            return connection

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        "src.infrastructure.smtp_client.smtplib.SMTP",
        FakeSMTP,
    )

    client = SMTPClient(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
        timeout=10,
    )

    message = EmailMessage()
    message["From"] = "user@example.com"
    message["To"] = "recipient@example.com"
    message["Subject"] = "Test"
    message.set_content("Hello")

    client.send_message(message)

    assert connection.calls[0] == (
        "connect",
        "smtp.example.com",
        587,
        10,
    )

    assert ("starttls",) in connection.calls
    assert ("login", "user@example.com", "secret") in connection.calls

    send_calls = [
        call
        for call in connection.calls
        if call[0] == "send_message"
    ]

    assert len(send_calls) == 1
    assert send_calls[0][1] is message
