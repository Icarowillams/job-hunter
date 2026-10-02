import json
from pathlib import Path
from src.application.bootstrap import build_application
from src.domain.models import Job
from src.infrastructure.email_notifier import EmailNotifier
from src.infrastructure.notification_repository import NotificationRepository
from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector
from src.local_report import generate_local_report, safe_link
from src.main import cli


class Collector:
    def fetch_jobs(self):
        return [Job(id='same-job', source='test', title='<script>test</script> Developer Junior',
                    company='Example', description='Python', location='Brasil', work_mode='remote',
                    url='javascript:alert(1)')]


def config(tmp_path, email=False):
    (tmp_path/'profile.json').write_text(json.dumps({'id':'test','skills':['python']}))
    p=tmp_path/'config.yaml'
    p.write_text('paths:\n  profile: profile.json\n  db: test.db\nnotification:\n  enabled: '+str(email).lower()+'\nserpapi:\n  api_key: synthetic-test\n  query_params:\n    query: junior\n')
    return p


def test_real_repository_deduplicates_sends_across_runs(tmp_path):
    runner=build_application(config_path=config(tmp_path), collector=Collector())
    class SMTP:
        calls=0
        def send_message(self, message): self.calls += 1
    smtp=SMTP()
    runner.notifier=EmailNotifier(smtp,'from@example.com','to@example.com',notification_repository=NotificationRepository(runner.job_repository.database))
    assert runner.run_once().notified == 1
    assert runner.run_once().notified == 0
    assert smtp.calls == 1
    with runner.job_repository.database.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM notification WHERE status='SENT'").fetchone()[0] == 1


def test_failed_email_can_retry_next_round(tmp_path):
    runner=build_application(config_path=config(tmp_path), collector=Collector())
    class SMTP:
        calls=0
        def send_message(self, message):
            self.calls += 1
            if self.calls == 1: raise RuntimeError('temporary failure')
    smtp=SMTP()
    runner.notifier=EmailNotifier(smtp,'from@example.com','to@example.com',notification_repository=NotificationRepository(runner.job_repository.database))
    first=runner.run_once()
    assert first.notified == 0 and first.errors
    assert runner.run_once().notified == 1
    assert runner.run_once().notified == 0
    assert smtp.calls == 2


def test_report_latest_analysis_once_and_safe_html(tmp_path):
    runner=build_application(config_path=config(tmp_path), collector=Collector())
    runner.run_once()
    result=runner.run_once()
    report=generate_local_report(result,db_path=runner.job_repository.database.db_path,output_path=tmp_path/'report.html')
    text=Path(report).read_text()
    assert text.count('<article>') == 1
    assert '<script>' not in text
    assert 'javascript:alert' not in text
    assert '&lt;script&gt;' in text
    assert safe_link('https://example.com') == 'https://example.com'
    assert safe_link('file:///etc/passwd') is None


def test_check_never_collects_or_creates_database(tmp_path, monkeypatch):
    p=config(tmp_path)
    monkeypatch.setattr(SerpApiJobCollector,'fetch_jobs',lambda self: (_ for _ in ()).throw(AssertionError('should not collect')))
    assert cli(['--check','--config',str(p)]) == 0
    assert not (tmp_path/'test.db').exists()


def test_dry_run_disables_email_before_bootstrap(tmp_path,monkeypatch):
    p=config(tmp_path,email=True)
    monkeypatch.setattr(SerpApiJobCollector,'fetch_jobs',lambda self: Collector().fetch_jobs())
    monkeypatch.setattr(EmailNotifier,'send_notification',lambda *a: (_ for _ in ()).throw(AssertionError('must not send')))
    assert cli(['--dry-run','--config',str(p)]) == 0
    assert (tmp_path/'reports/latest.html').exists()


def test_missing_key_diagnostic(tmp_path,monkeypatch,capsys):
    p=config(tmp_path)
    p.write_text(p.read_text().replace('synthetic-test','${SERPAPI_API_KEY}'))
    monkeypatch.delenv('SERPAPI_API_KEY',raising=False)
    assert cli(['--check','--config',str(p)]) == 2
    assert 'PENDENTE' in capsys.readouterr().out
    assert not (tmp_path/'test.db').exists()
