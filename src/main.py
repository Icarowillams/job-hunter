"""One-shot personal CLI. Scheduling is owned by Windows, not this process."""
import argparse
import sys
from pathlib import Path
from src.application.bootstrap import build_application, _load_config, _resolve_env_value
from src.infrastructure.profile_loader import ProfileLoader
from src.local_report import generate_local_report
from src.safe_errors import safe_error
from src.daily_digest import DailyDigest
from src.application.bootstrap import _build_email_notifier
from src.infrastructure.database import Database
from email.message import EmailMessage


def main():
    # Preserve programmatic API and legacy unit tests.
    runner = build_application()
    return runner.run_once()


def check_configuration(config_path, *, skip_email=False, skip_search=False):
    config_path = Path(config_path).resolve()
    config = _load_config(config_path)
    root = config_path.parent
    path = Path(config.get('paths', {}).get('profile', 'data/profile.json'))
    profile = ProfileLoader().load(path if path.is_absolute() else root/path)
    issues = []
    serpapi = config.get('serpapi', {})
    key = _resolve_env_value(serpapi.get('api_key', ''))
    if not skip_search and (not key or key.startswith('your_')):
        issues.append('SERPAPI_API_KEY ausente: preencha .env localmente.')
    searches = serpapi.get('searches', [])
    if not searches:
        searches = [serpapi.get('query_params', {})]
    if not 1 <= len(searches) <= 6:
        issues.append('Configure de 1 a 6 consultas de busca.')
    for search in searches:
        if not isinstance(search, dict) or not search.get('query', '').strip():
            issues.append('Consulta de busca vazia ou invalida.')
        elif not 1 <= int(search.get('limit', 10)) <= 20:
            issues.append('Cada consulta deve limitar resultados entre 1 e 20.')
    enabled = config.get('notification', {}).get('enabled', False)
    if (enabled or skip_search) and not skip_email:
        email = config.get('email', {})
        for field in ('smtp_server', 'username', 'password', 'from', 'to'):
            if not _resolve_env_value(email.get(field, '')):
                issues.append('Configuracao SMTP incompleta: '+field)
    print('Perfil profissional carregado. Consultas:', len(searches))
    print('E-mail:', 'desabilitado nesta execucao' if skip_email or not enabled else 'habilitado')
    for issue in issues:
        print('PENDENTE:', issue)
    if not issues:
        print('Configuracao estrutural OK. Chaves e entrega ainda precisam de validacao real.')
    return issues


def _cli(argv=None):
    parser = argparse.ArgumentParser(description='Job Hunter pessoal — busca, analise e relatorio local.')
    parser.add_argument('--config', default='config.yaml', help='Caminho do config.yaml')
    parser.add_argument('--check', action='store_true', help='Confere configuracao sem rede e sem criar banco')
    parser.add_argument('--dry-run', action='store_true', help='Busca REAL (consome API), persiste resultados, sem e-mail')
    parser.add_argument('--open-report', action='store_true', help='Abre o HTML local no navegador')
    parser.add_argument('--test-email', action='store_true', help='Envia um e-mail real de teste, sem buscar vagas')
    parser.add_argument('--retry-uncertain-email', action='store_true', help='Repete entrega incerta; pode duplicar e-mail. Confira a caixa antes.')
    args = parser.parse_args(argv)
    if args.test_email and (args.dry_run or args.check):
        parser.error('--test-email nao pode ser combinado com --dry-run ou --check')
    config_path = Path(args.config).resolve()
    try:
        if check_configuration(config_path, skip_email=args.dry_run, skip_search=args.test_email):
            return 2
        if args.check:
            return 0
        config = _load_config(config_path)
        if args.test_email:
            path = Path(config.get('paths', {}).get('db', 'data/job_hunter.db'))
            database = Database(str(path if path.is_absolute() else config_path.parent/path))
            email = _build_email_notifier(config, database)
            message = EmailMessage()
            message['From'], message['To'] = email.sender, email.recipient
            message['Subject'] = '[Job Hunter] Teste de envio local'
            message.set_content('Teste enviado pelo Job Hunter no notebook. Nenhuma busca de vagas ou candidatura foi realizada.')
            email.smtp_client.send_message(message)
            print('Teste aceito pelo servidor SMTP. Confira a caixa de entrada e o spam.')
            return 0
        # Only the consolidated digest may send in the local CLI. No per-job messages.
        runner = build_application(config_path=config_path, notifications_enabled=False)
        result = runner.run_once()
        report = generate_local_report(result, db_path=runner.job_repository.database.db_path,
            output_path=config_path.parent/'reports/latest.html', open_browser=args.open_report)
        print('Relatorio:', report)
        if config.get('notification', {}).get('enabled', False) and not args.dry_run:
            email = _build_email_notifier(config, runner.job_repository.database)
            digest = DailyDigest(runner.job_repository.database, email.smtp_client, email.sender, email.recipient,
                minimum_score=int(config.get('notification', {}).get('minimum_score', 70)))
            delivery = digest.send(result, retry_uncertain=args.retry_uncertain_email)
            result.notified = 1 if delivery == 'sent' else 0
            generate_local_report(result, db_path=runner.job_repository.database.db_path, output_path=config_path.parent/'reports/latest.html')
            print('Resumo diario:', 'aceito pelo servidor SMTP' if delivery == 'sent' else 'ja enviado hoje; nao repetido')
        print(f'Coletadas: {result.total_jobs} | Analisadas: {result.succeeded} | Falhas: {result.failed} | E-mails: {result.notified}')
        for error in result.errors:
            print('AVISO:', safe_error(error))
        return 1 if result.failed or result.errors else 0
    except Exception as exc:
        print('ERRO:', safe_error(exc), file=sys.stderr)
        return 1


def cli(argv=None):
    from src.local_lock import single_instance
    probe = argparse.ArgumentParser(add_help=False)
    probe.add_argument('--config', default='config.yaml')
    options, _ = probe.parse_known_args(argv)
    try:
        with single_instance(Path(options.config).resolve().parent/'data/run.lock'):
            return _cli(argv)
    except Exception as exc:
        print('ERRO:', safe_error(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(cli())
