"""Windows Task Scheduler entry; bounded log retention, no background Python loop."""
import contextlib
import os
from datetime import datetime
from pathlib import Path
from src.main import cli


def run():
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    logs = root/'logs'
    logs.mkdir(exist_ok=True)
    name = logs/('diario-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')
    with name.open('w', encoding='utf-8') as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        code = cli(['--config', str(root/'config.yaml')])
    for old in sorted(logs.glob('diario-*.log'), reverse=True)[30:]:
        old.unlink(missing_ok=True)
    return code


if __name__ == '__main__':
    raise SystemExit(run())
