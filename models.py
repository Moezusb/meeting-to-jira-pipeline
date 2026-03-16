"""
models.py
=========
Pydantic schema enforcement for Project Oracle V2.
All tickets must pass validation before export.
Zero schema failures = zero Jira sync errors.

Author: Mohamed Bah
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class JiraTicket(BaseModel):
    ticket_id: str
    summary: str = Field(..., description="Action-oriented title for the Jira ticket")
    issue_type: str = Field(..., pattern="^(Bug|Task|Story)$")
    priority: str = Field(..., pattern="^(Highest|High|Medium|Low)$")
    assignees: List[dict]
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    context: str
    labels: List[str] = []
    revenue_risk: bool = False
    revenue_client: Optional[str] = None
    client_arr: Optional[int] = None
    client_status: Optional[str] = None
