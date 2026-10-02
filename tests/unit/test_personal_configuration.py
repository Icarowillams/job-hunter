import json
import pytest
from src.application.bootstrap import build_application, _build_serpapi_collector
from src.ingestion.collectors.multi_query_collector import MultiQueryCollector
from src.domain.models import Job
from src.safe_errors import safe_error


def test_strict_missing_key_is_not_zero_jobs(monkeypatch):
    monkeypatch.delenv('SERPAPI_API_KEY', raising=False)
    with pytest.raises(ValueError, match='SERPAPI_API_KEY'):
        _build_serpapi_collector({'strict_config': True, 'serpapi': {'api_key': '${SERPAPI_API_KEY}'}})


def test_three_searches_are_bounded():
    c = _build_serpapi_collector({'serpapi': {'api_key': 'synthetic', 'searches': [
        {'query': 'frontend junior', 'limit': 100}, {'query': 'backend junior'}, {'query': 'fullstack junior'}
    ]}})
    assert len(c.collectors) == 3
    assert c.collectors[0].limit == 20


def test_multi_search_deduplicates():
    class Fake:
        def fetch_jobs(self):
            return [Job(id='one', source='test', title='Developer', company='Test', description='Python', url='https://example.com/job')]
    assert len(MultiQueryCollector([Fake(), Fake()]).fetch_jobs()) == 1


def test_paths_are_relative_to_configuration(tmp_path):
    (tmp_path/'profile.json').write_text(json.dumps({'id':'test','skills':['python']}))
    (tmp_path/'config.yaml').write_text('paths:\n  profile: profile.json\n  db: db.sqlite\nnotification:\n  enabled: false\n')
    runner = build_application(config_path=tmp_path/'config.yaml')
    assert runner.profile.id == 'test'
    assert (tmp_path/'db.sqlite').exists()


def test_secret_errors_redacted(monkeypatch):
    monkeypatch.setenv('SERPAPI_API_KEY', 'private-test-key')
    assert 'private-test-key' not in safe_error(Exception('error api_key=private-test-key&engine=test'))


def test_duplicate_notifier_false_not_counted(tmp_path):
    class FakeCollector:
        def fetch_jobs(self):
            return [Job(id='one',source='test',title='Developer',company='Example',description='Python')]
    class FakeNotifier:
        def send_notification(self, analysis, job):
            return False
    (tmp_path/'profile.json').write_text(json.dumps({'id':'test','skills':['python']}))
    (tmp_path/'config.yaml').write_text('paths:\n  profile: profile.json\n  db: db.sqlite\nnotification:\n  enabled: true\n')
    runner=build_application(config_path=tmp_path/'config.yaml', collector=FakeCollector(), notifier=FakeNotifier())
    result=runner.run_once()
    assert result.succeeded == 1
    assert result.notified == 0
