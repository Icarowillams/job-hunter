"""Redact configured secrets before displaying or persisting operational errors."""
import os
import re


def safe_error(error):
    text = str(error)
    for name, value in os.environ.items():
        if len(value) >= 4 and any(x in name.upper() for x in ('API_KEY', 'TOKEN', 'PASSWORD', 'SECRET')):
            text = text.replace(value, '[REDACTED]')
    return re.sub(r'(?i)(api_key|password|token)([=:\s]+)([^&\s]+)', r'\1\2[REDACTED]', text)
