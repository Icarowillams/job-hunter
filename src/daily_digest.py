"""One daily SMTP digest, entirely on the user's computer. No hosted components."""
import json
import smtplib
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from src.local_report import safe_link
from src.safe_errors import safe_error


class DailyDigest:
    def __init__(self, database, smtp_client, sender, recipient, minimum_score=70, max_jobs=15):
        self.database, self.smtp_client = database, smtp_client
        self.sender, self.recipient = sender, recipient.strip().lower()
        self.minimum_score, self.max_jobs = minimum_score, max_jobs
        with database.connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS daily_digest (
                    recipient TEXT NOT NULL, day TEXT NOT NULL, state TEXT NOT NULL,
                    message_id TEXT, updated_at TEXT, error TEXT,
                    PRIMARY KEY(recipient, day)
                );
                CREATE TABLE IF NOT EXISTS digest_delivered_job (
                    recipient TEXT NOT NULL, job_id TEXT NOT NULL, day TEXT NOT NULL,
                    PRIMARY KEY(recipient, job_id)
                );
            ''')

    def _items(self, result):
        items = []
        with self.database.connect() as conn:
            conn.row_factory = __import__('sqlite3').Row
            for processed in result.results:
                if not processed.success:
                    continue
                row = conn.execute('''
                    SELECT j.id,j.title,j.company,j.location,j.work_mode,j.url,
                           a.compatibility_score,a.hard_blocker,a.breakdown,a.strengths,a.gaps
                    FROM job j JOIN job_analysis a ON a.job_id=j.id
                    WHERE j.id=? AND NOT EXISTS (
                        SELECT 1 FROM digest_delivered_job d WHERE d.recipient=? AND d.job_id=j.id
                    ) ORDER BY a.rowid DESC LIMIT 1
                ''', (processed.job_id, self.recipient)).fetchone()
                if row is None:
                    continue
                item = dict(row)
                breakdown = json.loads(item['breakdown'] or '{}')
                eligibility = breakdown.get('eligibility', {})
                status = eligibility.get('status', 'review')
                if status in ('rejected', 'ineligible', 'blocked'):
                    continue
                if (item['compatibility_score'] or 0) < self.minimum_score:
                    continue
                item['review'] = bool(item['hard_blocker']) or status != 'eligible'
                item['reasons'] = eligibility.get('reasons', [])
                item['resume'] = breakdown.get('recommended_resume', 'conferir manualmente')
                items.append(item)
        items.sort(key=lambda item: (item['review'], -(item['compatibility_score'] or 0)))
        return items[:self.max_jobs]

    def send(self, result, *, today=None, retry_uncertain=False):
        """Returns sent/already_sent. Ambiguous SMTP outcomes require explicit local retry."""
        day = (today or date.today()).isoformat()  # Windows local date; scheduler uses same clock.
        message_id = make_msgid(domain='job-hunter.local')
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute('SELECT state FROM daily_digest WHERE recipient=? AND day=?', (self.recipient, day)).fetchone()
            if old and old[0] == 'SENT':
                return 'already_sent'
            if old and old[0] in ('SENDING', 'UNCERTAIN') and not retry_uncertain:
                raise RuntimeError('Entrega anterior incerta/em andamento. Confira a caixa de entrada antes de usar --retry-uncertain-email; esse comando pode duplicar o resumo.')
            conn.execute('''INSERT INTO daily_digest(recipient,day,state,message_id,updated_at,error)
                VALUES(?,?,'SENDING',?,?,NULL) ON CONFLICT(recipient,day)
                DO UPDATE SET state='SENDING',message_id=excluded.message_id,updated_at=excluded.updated_at,error=NULL''',
                (self.recipient, day, message_id, now))
        try:
            items = self._items(result)
            incomplete = bool(result.failed or result.errors)
            subject = 'Busca com falhas' if incomplete else f'{len(items)} novas vagas selecionadas'
            message = EmailMessage()
            message['From'], message['To'] = self.sender, self.recipient
            message['Subject'] = f'[Job Hunter] {day} — {subject}'
            message['Message-ID'] = message_id
            message['Date'] = __import__('email.utils', fromlist=['formatdate']).formatdate(localtime=True)
            lines = ['Bom dia! Seu resumo diário do Job Hunter.', '',
                f'Coletadas: {result.total_jobs} | Analisadas: {result.succeeded} | Falhas: {result.failed}',
                f'Novas selecionadas neste resumo: {len(items)} (limite de {self.max_jobs}).',
                'Novas significa ainda não incluídas em resumo anterior para este destinatário.', '']
            if incomplete:
                lines += ['ATENÇÃO: a busca não foi concluída integralmente. Ausência de resultados não significa ausência de vagas.',
                          *[safe_error(e)[:500] for e in result.errors], '']
            elif not items:
                lines += ['Nenhuma novidade que atenda aos filtros e à pontuação mínima nesta rodada.',
                          'Isso não significa que não existam vagas disponíveis no mercado.', '']
            for number, item in enumerate(items, 1):
                lines += [f'{number}. {item["title"]} — {item["company"]}',
                    f'{item["location"] or "Local não informado"} | {item["work_mode"] or "Modalidade não informada"}',
                    ('REVISÃO MANUAL — não confirmada como elegível' if item['review'] else 'Compatível com os filtros pessoais'),
                    f'Compatibilidade técnica: {item["compatibility_score"]}/100; não é probabilidade de contratação.',
                    'Por que entrou: '+('; '.join(item['reasons']) or 'Conferir requisitos no anúncio.'),
                    'Competências atendidas: '+', '.join(json.loads(item['strengths'] or '[]')),
                    'Lacunas: '+(', '.join(json.loads(item['gaps'] or '[]')) or 'Nenhuma identificada pelas regras.'),
                    'Currículo sugerido: '+str(item['resume']),
                    'Link: '+(safe_link(item['url']) or 'Sem link seguro; confira o relatório local.'), '']
            lines += ['Confira o anúncio original antes de se candidatar. Não foram enviadas candidaturas ou currículos.',
                      'Histórico completo no notebook: reports/latest.html.',
                      'Mensagem produzida e enviada pelo Job Hunter do seu notebook.']
            message.set_content('\n'.join(lines))
        except Exception as exc:
            self._state(day, 'FAILED', exc)
            raise
        try:
            self.smtp_client.send_message(message)
        except Exception as exc:
            # These failures prove SMTP did not accept the message; other failures may follow DATA acceptance.
            known_unsent = isinstance(exc, (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused,
                smtplib.SMTPSenderRefused, smtplib.SMTPConnectError, ConnectionRefusedError))
            self._state(day, 'FAILED' if known_unsent else 'UNCERTAIN', exc)
            raise
        with self.database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            for item in items:
                conn.execute('INSERT OR IGNORE INTO digest_delivered_job VALUES(?,?,?)', (self.recipient, item['id'], day))
            conn.execute("UPDATE daily_digest SET state='SENT',updated_at=?,error=NULL WHERE recipient=? AND day=?", (now,self.recipient,day))
        return 'sent'

    def _state(self, day, state, error):
        with self.database.connect() as conn:
            conn.execute('UPDATE daily_digest SET state=?,error=? WHERE recipient=? AND day=?',
                         (state, safe_error(error), self.recipient, day))
