from src.domain.enums import NotificationChannel


def test_notification_channel_supports_email():
    assert NotificationChannel.EMAIL.value == "email"
