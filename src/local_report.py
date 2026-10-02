"""Private static report; job text is untrusted and never inserted as raw HTML."""
import html
import json
import sqlite3
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


def escaped(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def safe_link(url):
    try:
        parsed = urlsplit(url or '')
        return url if parsed.scheme in ('http', 'https') and parsed.netloc else None
    except ValueError:
        return None


def parsed_json(value, default):
    try:
        return json.loads(value) if value else default
    except (ValueError, TypeError):
        return default


def generate_local_report(run_result=None, db_path='data/job_hunter.db', profile_path=None,
                          output_path='reports/latest.html', open_browser=False):
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute('''
            SELECT j.*, a.compatibility_score, a.hard_blocker, a.classification,
                   a.breakdown, a.strengths, a.gaps, a.unknown_requirements
            FROM job j LEFT JOIN job_analysis a ON a.rowid = (
                SELECT ax.rowid FROM job_analysis ax WHERE ax.job_id = j.id ORDER BY ax.rowid DESC LIMIT 1
            ) ORDER BY COALESCE(a.hard_blocker, 1), a.compatibility_score DESC, j.updated_at DESC LIMIT 250
        ''').fetchall()
    current = {r.job_id for r in getattr(run_result, 'results', [])}
    body = [f'<h1>Job Hunter pessoal</h1><p>Gerado em {escaped(datetime.now().strftime("%d/%m/%Y %H:%M"))} — horário local.</p>',
            '<p>Histórico local: última análise por vaga, até 250 registros. A presença aqui não confirma que a vaga continua aberta. A nota é técnica, não probabilidade de contratação.</p>']
    if run_result is not None:
        body.append(f'<section><b>Esta rodada:</b> {run_result.total_jobs} vagas coletadas · {run_result.succeeded} analisadas · {run_result.failed} falhas · {run_result.notified} avisos enviados.</section>')
        for error in getattr(run_result, 'errors', []):
            body.append('<p class="warning">'+escaped(error)+'</p>')
    if not rows:
        body.append('<section>Nenhuma vaga armazenada. Uma busca sem resultados não comprova indisponibilidade no mercado.</section>')
    for row in rows:
        job = dict(row)
        breakdown = parsed_json(job.get('breakdown'), {})
        eligibility = breakdown.get('eligibility', {})
        status = eligibility.get('status', 'review' if job.get('hard_blocker') else 'eligible')
        labels = {'eligible': 'Elegível pelos filtros', 'review': 'Revisar manualmente', 'ineligible': 'Fora dos filtros', 'blocked': 'Fora dos filtros', 'rejected': 'Fora dos filtros'}
        label = labels.get(status, str(status))
        if job.get('hard_blocker') and status == 'eligible':
            label = 'Revisar requisitos obrigatórios'
        reasons = eligibility.get('reasons', [])
        curriculum = breakdown.get('recommended_resume', breakdown.get('recommended_curriculum', breakdown.get('curriculum', 'Ver perfil da vaga')))
        body.append('<article><small>'+('Encontrada nesta rodada' if job['id'] in current else 'Histórico — não coletada nesta rodada')+'</small>')
        body.append(f'<h2>{escaped(job["title"])}</h2><p>{escaped(job["company"])} · {escaped(job["location"])} · {escaped(job["work_mode"])}</p>')
        body.append(f'<p><b>{escaped(label)}</b> · Compatibilidade técnica: {escaped(job.get("compatibility_score"))}/100</p>')
        if reasons:
            body.append('<ul>'+''.join('<li>'+escaped(r)+'</li>' for r in reasons)+'</ul>')
        for field, title in [('strengths','Atendidos'), ('gaps','Lacunas'), ('unknown_requirements','Não confirmados')]:
            values = parsed_json(job.get(field), [])
            if values:
                body.append(f'<p><b>{title}:</b> {escaped(", ".join(values))}</p>')
        body.append(f'<p>Versão de currículo sugerida: <b>{escaped(curriculum)}</b>. Envio manual.</p>')
        url = safe_link(job.get('url'))
        if url:
            body.append(f'<p><a href="{escaped(url)}" target="_blank" rel="noopener noreferrer">Abrir anúncio original</a></p>')
        body.append('<details><summary>Descrição da vaga</summary><pre>'+escaped(job.get('description'))+'</pre></details></article>')
    document = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Hunter — relatório local</title><style>
:root{color-scheme:light dark}body{font-family:system-ui,sans-serif;max-width:950px;margin:32px auto;padding:0 20px;line-height:1.6}article,section{border:1px solid #8886;padding:20px;border-radius:12px;margin:18px 0}h1{font-size:30px}h2{font-size:20px}small{opacity:.7}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}a{color:LinkText}.warning{border-left:3px solid;padding-left:12px}
</style><body>'''+''.join(body)+'</body></html>'
    out.write_text(document, encoding='utf-8')
    if open_browser:
        webbrowser.open(out.resolve().as_uri())
    return str(out)
