from types import SimpleNamespace

from src.application.notification.notifier import Notifier


class FakeNotifier(Notifier):
    def send_notification(self, analysis, job):
        return None


def test_notifier_defines_send_notification_contract():
    notifier = FakeNotifier()

    notifier.send_notification(
        analysis=SimpleNamespace(),
        job=SimpleNamespace(),
    )
