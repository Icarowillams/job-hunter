from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Metric(BaseModel):
    id: str
    name: str
    value: int
    created_at: datetime
    execution_id: Optional[str] = None
