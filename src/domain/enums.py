from enum import Enum


class ExecutionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationChannel(str, Enum):
    CONSOLE = "console"
    TELEGRAM = "telegram"


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class JobClassification(str, Enum):
    PRIORITY = "PRIORITY"
    REVIEW = "REVIEW"
    IGNORE = "IGNORE"
