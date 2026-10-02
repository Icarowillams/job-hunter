import json
import smtplib
from datetime import date
from types import SimpleNamespace
import pytest
from src.application.bootstrap import build_application
from src.application.orchestrator import RunResult
from src.daily_digest import DailyDigest
from src.domain.models import Job
from src.local_lock import single_instance
from src.main import cli


class SMTP:
    def __init__(self): self.messages=[]
    def send_message(self,message): self.messages.append(message)


@pytest.fixture
def setup(tmp_path):
    (tmp_path/'profile.json').write_text(json.dumps({'id':'test','skills':['python']}))
    config=tmp_path/'config.yaml'
    config.write_text('paths:\n  profile: profile.json\n  db: db.sqlite\nnotification:\n  enabled: false\nserpapi:\n  api_key: test-placeholder\n  query_params:\n    query: junior\n')
    class Collector:
        def fetch_jobs(self):
            return [Job(id='one',source='test',title='Python Developer Junior',company='Example',description='Python',location='Brasil',work_mode='remote',url='https://example.com/job')]
    runner=build_application(config_path=config,collector=Collector())
    result=runner.run_once()
    smtp=SMTP()
    digest=DailyDigest(runner.job_repository.database,smtp,'from@example.com','to@example.com')
    return runner,result,smtp,digest,config


def test_digest_once_per_day_newness_across_days(setup):
    runner,result,smtp,digest,_=setup
    assert digest.send(result,today=date(2026,9,15)) == 'sent'
    assert digest.send(result,today=date(2026,9,15)) == 'already_sent'
    assert len(smtp.messages) == 1
    text=smtp.messages[0].get_content()
    assert 'Python Developer Junior' in text and 'https://example.com/job' in text
    assert digest.send(result,today=date(2026,9,16)) == 'sent'
    assert len(smtp.messages) == 2
    assert 'Nenhuma novidade' in smtp.messages[1].get_content()
    assert 'Python Developer Junior' not in smtp.messages[1].get_content()


def test_zero_jobs_still_daily_email(setup):
    _,_,smtp,digest,_=setup
    digest.send(RunResult(0,0,0,0,0))
    assert 'Nenhuma novidade' in smtp.messages[0].get_content()


def test_failed_collection_is_not_no_jobs(setup):
    _,_,smtp,digest,_=setup
    digest.send(RunResult(0,0,0,0,0,errors=['SerpAPI indisponível']))
    assert 'Busca com falhas' in smtp.messages[0]['Subject']
    assert 'Nenhuma novidade' not in smtp.messages[0].get_content()
    assert 'ATENÇÃO' in smtp.messages[0].get_content()


def test_auth_failure_can_retry_without_marking_items_sent(setup):
    runner,result,smtp,digest,_=setup
    class Bad:
        def send_message(self,message): raise smtplib.SMTPAuthenticationError(535,b'denied')
    digest.smtp_client=Bad()
    with pytest.raises(smtplib.SMTPAuthenticationError): digest.send(result)
    with runner.job_repository.database.connect() as conn:
        assert conn.execute('SELECT state FROM daily_digest').fetchone()[0]=='FAILED'
        assert conn.execute('SELECT count(*) FROM digest_delivered_job').fetchone()[0]==0
    digest.smtp_client=smtp
    assert digest.send(result)=='sent'


def test_uncertain_send_not_automatically_retried(setup):
    _,result,smtp,digest,_=setup
    class Bad:
        def send_message(self,message): raise TimeoutError('unknown delivery')
    digest.smtp_client=Bad()
    with pytest.raises(TimeoutError): digest.send(result)
    digest.smtp_client=smtp
    with pytest.raises(RuntimeError,match='incerta'): digest.send(result)
    assert len(smtp.messages)==0
    assert digest.send(result,retry_uncertain=True)=='sent'


def test_rejected_excluded_and_review_labelled(setup):
    runner,result,smtp,digest,_=setup
    db=runner.job_repository.database
    with db.connect() as conn:
        conn.execute('UPDATE job_analysis SET breakdown=?,hard_blocker=1',(json.dumps({'eligibility':{'status':'rejected','reasons':['Senior']}}),))
    digest.send(result,today=date(2026,9,15))
    assert 'Python Developer Junior' not in smtp.messages[-1].get_content()
    with db.connect() as conn:
        conn.execute('UPDATE job_analysis SET breakdown=?,hard_blocker=1',(json.dumps({'eligibility':{'status':'review','reasons':['Portugal: confirmar Brasil']},'recommended_resume':'backend'}),))
    digest.send(result,today=date(2026,9,16))
    assert 'REVISÃO MANUAL' in smtp.messages[-1].get_content()
    assert 'Portugal: confirmar Brasil' in smtp.messages[-1].get_content()


def test_lock_prevents_overlap_and_releases(tmp_path):
    path=tmp_path/'lock'
    with single_instance(path):
        with pytest.raises(RuntimeError,match='andamento'):
            with single_instance(path): pass
    with single_instance(path): pass


def test_test_email_never_collects(setup,monkeypatch):
    _,_,smtp,_,config=setup
    config.write_text(config.read_text()+'email:\n  smtp_server: smtp.example.com\n  username: synthetic\n  password: synthetic\n  from: from@example.com\n  to: to@example.com\n')
    monkeypatch.setattr('src.main._build_email_notifier',lambda *args:SimpleNamespace(sender='from@example.com',recipient='to@example.com',smtp_client=smtp))
    monkeypatch.setattr('src.main.build_application',lambda **kw: (_ for _ in ()).throw(AssertionError('no collection')))
    assert cli(['--config',str(config),'--test-email'])==0
    assert len(smtp.messages)==1
    assert 'Teste' in smtp.messages[0]['Subject']


def test_cli_uses_digest_not_individual_email(setup,monkeypatch):
    runner,result,smtp,_,config=setup
    config.write_text(config.read_text().replace('enabled: false','enabled: true')+'email:\n  smtp_server: smtp.example.com\n  username: synthetic\n  password: synthetic\n  from: from@example.com\n  to: to@example.com\n')
    def build(**kwargs):
        assert kwargs['notifications_enabled'] is False
        runner.notifier=None
        return runner
    monkeypatch.setattr('src.main.build_application',build)
    monkeypatch.setattr('src.main._build_email_notifier',lambda *args:SimpleNamespace(sender='from@example.com',recipient='to@example.com',smtp_client=smtp))
    assert cli(['--config',str(config)])==0
    assert len(smtp.messages)==1
    assert cli(['--config',str(config)])==0
    assert len(smtp.messages)==1


def test_scheduled_entry_writes_log_and_trims(tmp_path,monkeypatch):
    import src.scheduled as scheduled
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(scheduled,'__file__',str(tmp_path/'src/scheduled.py'))
    def fake_cli(argv):
        assert str(tmp_path/'config.yaml') in argv
        print('synthetic run')
        return 0
    monkeypatch.setattr(scheduled,'cli',fake_cli)
    logs=tmp_path/'logs';logs.mkdir()
    for n in range(35): (logs/f'diario-20000101-{n:06}.log').write_text('old')
    assert scheduled.run()==0
    files=list(logs.glob('diario-*.log'))
    assert len(files)==30
    assert any('synthetic run' in p.read_text() for p in files)


def test_only_included_items_marked_delivered(setup):
    runner,result,smtp,digest,_=setup
    digest.max_jobs=0
    digest.send(result,today=date(2026,9,15))
    with runner.job_repository.database.connect() as conn:
        assert conn.execute('SELECT count(*) FROM digest_delivered_job').fetchone()[0]==0
    digest.max_jobs=15
    digest.send(result,today=date(2026,9,16))
    assert 'Python Developer Junior' in smtp.messages[-1].get_content()
