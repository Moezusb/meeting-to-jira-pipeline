from pydantic import BaseModel, Field
from typing import List, Optional

class JiraTicket(BaseModel):
    ticket_id: str
    summary: str = Field(..., description="Action-oriented title")
    issue_type: str = Field(..., pattern="^(Bug|Task|Story)$")
    priority: str = Field(..., pattern="^(Highest|High|Medium|Low)$")
    assignees: List[dict]
    due_date: str
    context: str
    labels: List[str] = []
    revenue_risk: bool = False  # New MBA-level metric
