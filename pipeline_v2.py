"""
pipeline_v2.py
==============
Project Oracle V2: Revenue-Aware Action Intelligence Engine.

Self-contained pipeline that:
  1. Parses a meeting transcript into structured action items
  2. Classifies each item by type and base priority
  3. Enriches tickets against the Revenue Bridge (high-value client list)
  4. Escalates priority to Highest for any At-Risk client mentions
  5. Validates all tickets against the Pydantic schema
  6. Exports production-ready JSON

Run:
    python pipeline_v2.py

Author: Mohamed Bah
"""

import os
import json
from datetime import datetime, timedelta
from models import JiraTicket
from transcript_parser import parse_transcript


# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────

TRANSCRIPT_PATH      = "meeting_transcript.txt"
CLIENTS_PATH         = "high_value_clients.json"
OUTPUT_PATH          = "jira_v2_production_ready.json"
MEETING_DATE         = datetime(2026, 3, 14)   # Anchors all due date calculations


# ─────────────────────────────────────────────────────────
# CLASSIFICATION ENGINE
# Maps action item signals to Jira issue types and priority
# ─────────────────────────────────────────────────────────

ISSUE_TYPE_RULES = [
    (["bug", "fix", "truncat", "error", "crash", "broken", "regression"], "Bug"),
    (["story", "redesign", "onboard", "ui", "design", "flow"],            "Story"),
]

PRIORITY_RULES = [
    (["today", "urgent", "blocking", "critical", "immediately"],           "High"),
    (["wednesday", "thursday", "monday", "tuesday", "friday", "eod"],     "Medium"),
    (["next week", "two weeks", "next sprint"],                            "Low"),
]

LABEL_RULES = [
    (["zendesk", "jira", "integration", "sync"],   "integration"),
    (["export", "csv", "truncat"],                 "data-export"),
    (["onboard", "design", "ui", "handoff"],       "design"),
    (["confluence", "automation", "auto-pop"],     "automation"),
    (["release", "changelog", "notes", "v2.4"],    "release"),
    (["regression", "qa", "testing"],              "qa"),
]


def classify_issue_type(text: str) -> str:
    text_lower = text.lower()
    for keywords, issue_type in ISSUE_TYPE_RULES:
        if any(kw in text_lower for kw in keywords):
            return issue_type
    return "Task"


def classify_priority(due_hint: str, text: str) -> str:
    combined = (due_hint + " " + text).lower()
    for keywords, priority in PRIORITY_RULES:
        if any(kw in combined for kw in keywords):
            return priority
    return "Medium"


def classify_labels(text: str) -> list:
    text_lower = text.lower()
    labels = []
    for keywords, label in LABEL_RULES:
        if any(kw in text_lower for kw in keywords):
            labels.append(label)
    return labels if labels else ["ops"]


# ─────────────────────────────────────────────────────────
# DUE DATE CALCULATOR
# Converts natural language hints to ISO date strings
# anchored to MEETING_DATE
# ─────────────────────────────────────────────────────────

DAY_OFFSETS = {
    "today":      0,
    "monday":     0,   # next occurrence calculated below
    "tuesday":    1,
    "wednesday":  2,
    "thursday":   3,
    "friday":     4,
    "this week":  4,
    "next week":  7,
    "two weeks":  14,
}

def resolve_due_date(hint: str) -> str:
    """
    Resolves a due hint to an ISO date string relative to MEETING_DATE.
    For weekday names, finds the next occurrence after the meeting date.
    """
    hint_lower = hint.lower()

    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    if hint_lower in weekdays:
        target_weekday = weekdays.index(hint_lower)
        meeting_weekday = MEETING_DATE.weekday()   # Saturday = 5 (meeting is a Saturday)
        days_ahead = (target_weekday - meeting_weekday) % 7
        if days_ahead == 0:
            days_ahead = 7
        due = MEETING_DATE + timedelta(days=days_ahead)
        return due.strftime("%Y-%m-%d")

    offset = DAY_OFFSETS.get(hint_lower, 7)
    return (MEETING_DATE + timedelta(days=offset)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────
# TICKET BUILDER
# Converts parsed action items into raw ticket dicts
# ─────────────────────────────────────────────────────────

def build_tickets(action_items: list) -> list:
    tickets = []
    for i, item in enumerate(action_items, 1):
        ticket_id  = f"AUTO-{i:03d}"
        text       = item["raw"]
        due_hint   = item["due_hint"]
        assignee   = item["assignee_hint"]

        assignees = [{"name": name.strip()} for name in assignee.split("+")]

        ticket = {
            "ticket_id":      ticket_id,
            "summary":        text[:120],
            "issue_type":     classify_issue_type(text),
            "priority":       classify_priority(due_hint, text),
            "assignees":      assignees,
            "due_date":       resolve_due_date(due_hint),
            "context":        item["context"],
            "labels":         classify_labels(text),
            "revenue_risk":   False,
            "revenue_client": None,
            "client_arr":     None,
            "client_status":  None,
        }
        tickets.append(ticket)
    return tickets


# ─────────────────────────────────────────────────────────
# REVENUE INTELLIGENCE GATE
# Cross-references tickets against the Revenue Bridge
# Escalates priority for any At-Risk or Watch client mention
# ─────────────────────────────────────────────────────────

def load_revenue_bridge(clients_path: str) -> list:
    if not os.path.exists(clients_path):
        print(f"  [warning] {clients_path} not found. Revenue enrichment skipped.")
        return []
    with open(clients_path, "r") as f:
        data = json.load(f)
    return data.get("clients", [])


def enrich_with_revenue_intelligence(ticket: dict, clients: list) -> dict:
    """
    Scans ticket summary and context for high-value client name mentions.
    Escalates priority to Highest for At-Risk clients.
    Escalates to High for Watch clients (if not already higher).
    """
    text = (ticket["summary"] + " " + ticket["context"]).lower()

    for client in clients:
        if client["name"].lower() in text:
            ticket["revenue_client"] = client["name"]
            ticket["client_arr"]     = client["arr"]
            ticket["client_status"]  = client["status"]
            ticket["revenue_risk"]   = True
            ticket["labels"].append("REVENUE-AT-RISK")

            if client["status"] == "At-Risk":
                ticket["priority"] = "Highest"
            elif client["status"] == "Watch" and ticket["priority"] not in ("Highest", "High"):
                ticket["priority"] = "High"

            break   # One client match per ticket is sufficient

    return ticket


# ─────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────

def process_pipeline():
    print("=" * 60)
    print("  PROJECT ORACLE V2 -- REVENUE-AWARE ACTION ENGINE")
    print("=" * 60)

    # Step 1: Parse transcript
    print(f"\n[1/4] Parsing transcript: {TRANSCRIPT_PATH}")
    action_items = parse_transcript(TRANSCRIPT_PATH)
    if not action_items:
        print("  No action items found. Exiting.")
        return
    print(f"  Extracted {len(action_items)} action items.")

    # Step 2: Build base tickets
    print(f"\n[2/4] Building and classifying tickets...")
    tickets = build_tickets(action_items)
    print(f"  {len(tickets)} tickets classified.")

    # Step 3: Revenue enrichment
    print(f"\n[3/4] Loading Revenue Bridge: {CLIENTS_PATH}")
    clients = load_revenue_bridge(CLIENTS_PATH)
    print(f"  {len(clients)} high-value clients loaded.")

    escalated = 0
    for ticket in tickets:
        before = ticket["priority"]
        ticket = enrich_with_revenue_intelligence(ticket, clients)
        if ticket["priority"] != before:
            escalated += 1
            print(f"  [ESCALATED] {ticket['ticket_id']} -- {ticket['revenue_client']} "
                  f"({ticket['client_status']}) -> {ticket['priority']}")

    print(f"  Revenue escalations: {escalated}")

    # Step 4: Schema validation and export
    print(f"\n[4/4] Validating schema and exporting...")
    validated_tickets = []
    errors = 0
    for raw in tickets:
        try:
            validated = JiraTicket(**raw)
            validated_tickets.append(validated.model_dump())
        except Exception as e:
            print(f"  [SCHEMA ERROR] {raw.get('ticket_id', '?')}: {e}")
            errors += 1

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(),
                   "ticket_count": len(validated_tickets),
                   "tickets": validated_tickets}, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Tickets validated : {len(validated_tickets)}")
    print(f"  Schema errors     : {errors}")
    print(f"  Revenue escalated : {escalated}")
    print(f"  Output            : {OUTPUT_PATH}")
    print(f"{'=' * 60}\n")

    # Summary table
    print(f"{'ID':<10} {'Priority':<10} {'Type':<8} {'Assignee':<22} {'Due':<12} Summary")
    print("-" * 90)
    for t in validated_tickets:
        assignee = ", ".join(a["name"] for a in t["assignees"])
        summary  = t["summary"][:36] + "..." if len(t["summary"]) > 36 else t["summary"]
        flag     = " [REVENUE]" if t["revenue_risk"] else ""
        print(f"{t['ticket_id']:<10} {t['priority']:<10} {t['issue_type']:<8} "
              f"{assignee:<22} {t['due_date']:<12} {summary}{flag}")


if __name__ == "__main__":
    process_pipeline()
