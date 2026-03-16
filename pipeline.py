"""
meeting-to-jira-pipeline
========================
Reads a meeting transcript, extracts action items, classifies
and prioritizes each one, and outputs structured Jira-ready tickets
as JSON -- with a visual summary chart.

Two extraction modes:
  --mode parsed   : extract action items directly from transcript (default)
  --mode hardcoded: use the curated action list (more precise, for demos)

Author : Mohamed Bah
Stack  : Python, JSON, Matplotlib
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from transcript_parser import parse_transcript, validate_extraction


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

TRANSCRIPT_FILE = "meeting_transcript.txt"
OUTPUT_JSON     = "jira_tickets_output.json"
OUTPUT_CHART    = "outputs/pipeline_summary.png"

TICKET_TYPE_MAP = {
    "bug":        {"issue_type": "Bug",   "default_priority": "High"},
    "task":       {"issue_type": "Task",  "default_priority": "Medium"},
    "automation": {"issue_type": "Story", "default_priority": "Medium"},
    "handoff":    {"issue_type": "Task",  "default_priority": "Medium"},
    "release":    {"issue_type": "Task",  "default_priority": "High"},
}

HIGH_PRIORITY_SIGNALS = [
    "blocking", "critical", "enterprise", "urgent", "high priority",
    "can't", "cannot", "broken", "bug", "three clients", "multiple clients",
]
LOW_PRIORITY_SIGNALS = [
    "nice to have", "eventually", "someday", "low priority", "minor",
]

ASSIGNEE_MAP = {
    "james":  {"name": "James Okafor",  "role": "Engineering Lead", "jira_id": "james.okafor"},
    "priya":  {"name": "Priya Mehta",   "role": "QA Lead",          "jira_id": "priya.mehta"},
    "tom":    {"name": "Tom Bergmann",  "role": "Customer Success",  "jira_id": "tom.bergmann"},
    "aisha":  {"name": "Aisha Diallo",  "role": "Design Lead",       "jira_id": "aisha.diallo"},
    "sarah":  {"name": "Sarah Chen",    "role": "Product Lead",      "jira_id": "sarah.chen"},
}

PRIORITY_COLORS = {
    "High":   "#003314",
    "Medium": "#6b9e7e",
    "Low":    "#d4e6da",
}

TYPE_COLORS = {
    "Bug":   "#003314",
    "Task":  "#6b9e7e",
    "Story": "#d4e6da",
}


# ─────────────────────────────────────────────
# CURATED ACTION ITEMS
# Used in --mode hardcoded for precise demos.
# In production this list is replaced by the
# transcript_parser output (or a Claude API call).
# ─────────────────────────────────────────────

CURATED_ACTIONS = [
    {
        "raw":           "Fix CSV export truncation bug, staging by Wednesday EOD",
        "assignee_hint": "james",
        "context":       "Three enterprise clients affected: Harlow Logistics, Meridian Technologies, Northgate Financial. Fields truncated at 256 chars. Legacy export handler issue.",
        "due_hint":      "wednesday",
    },
    {
        "raw":           "Regression testing on export module, sign-off by Thursday EOD",
        "assignee_hint": "priya",
        "context":       "Dependent on James completing bug fix in staging by Wednesday EOD. Full regression on export module required before ship.",
        "due_hint":      "thursday",
    },
    {
        "raw":           "Send holding message to Harlow Logistics, Meridian Technologies, Northgate Financial",
        "assignee_hint": "tom",
        "context":       "Client communication to acknowledge CSV export issue. Message already drafted as of meeting date.",
        "due_hint":      "today",
    },
    {
        "raw":           "Finalize onboarding redesign, hand off to engineering by Friday EOD",
        "assignee_hint": "aisha",
        "context":       "Empty state copy agreed in meeting: directive tone. Designs 90% complete at time of meeting.",
        "due_hint":      "friday",
    },
    {
        "raw":           "Build Confluence auto-population automation for test coverage metrics",
        "assignee_hint": "sarah",
        "context":       "Currently a 2-hour manual task every two weeks. Priya will provide the data source. Target: recurring Confluence page updated automatically.",
        "due_hint":      "next week",
    },
    {
        "raw":           "Spec and build Zendesk-to-Jira severity threshold integration",
        "assignee_hint": "sarah james",
        "context":       "Currently Tom manually copies Zendesk tickets to Jira each morning, taking 45 minutes. Spec this week, build in two weeks.",
        "due_hint":      "two weeks",
    },
    {
        "raw":           "Deliver technical changelog for v2.4 by Monday EOD",
        "assignee_hint": "james",
        "context":       "Required input for client-facing release notes. Sarah needs this to prepare the customer version by Tuesday.",
        "due_hint":      "monday",
    },
    {
        "raw":           "Transform technical changelog into client-facing release notes for v2.4",
        "assignee_hint": "sarah",
        "context":       "Based on James technical changelog. Only include v2.4 items. Deliver to Tom by Tuesday EOD.",
        "due_hint":      "tuesday",
    },
]


# ─────────────────────────────────────────────
# CLASSIFICATION HELPERS
# ─────────────────────────────────────────────

def detect_priority(text: str) -> str:
    text_lower = text.lower()
    if any(s in text_lower for s in HIGH_PRIORITY_SIGNALS):
        return "High"
    if any(s in text_lower for s in LOW_PRIORITY_SIGNALS):
        return "Low"
    return "Medium"


def detect_ticket_type(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["bug", "fix", "broken", "truncat", "error"]):
        return "bug"
    if any(w in text_lower for w in ["automat", "integration", "sync", "confluence", "zendesk-to-jira"]):
        return "automation"
    if any(w in text_lower for w in ["handoff", "design", "finalize", "deliver"]):
        return "handoff"
    if any(w in text_lower for w in ["release", "changelog", "release notes"]):
        return "release"
    return "task"


def extract_assignees(hint: str) -> list:
    hint_lower = hint.lower()
    if "sarah" in hint_lower and "james" in hint_lower:
        return [ASSIGNEE_MAP["sarah"], ASSIGNEE_MAP["james"]]
    for key, val in ASSIGNEE_MAP.items():
        if key in hint_lower:
            return [val]
    return [{"name": "Unassigned", "role": "TBD", "jira_id": "unassigned"}]


def parse_due_date(hint: str) -> str:
    hint_lower = hint.lower()
    today  = datetime.today()
    offsets = {
        "today":     0,
        "monday":    (0 - today.weekday()) % 7 or 7,
        "tuesday":   (1 - today.weekday()) % 7 or 7,
        "wednesday": (2 - today.weekday()) % 7 or 7,
        "thursday":  (3 - today.weekday()) % 7 or 7,
        "friday":    (4 - today.weekday()) % 7 or 7,
    }
    for keyword, days in offsets.items():
        if keyword in hint_lower:
            return (today + timedelta(days=days)).strftime("%Y-%m-%d")
    if "next week" in hint_lower or "two weeks" in hint_lower:
        return (today + timedelta(weeks=2)).strftime("%Y-%m-%d")
    return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

def build_tickets(actions: list) -> list:
    tickets = []
    for i, action in enumerate(actions, 1):
        ticket_type = detect_ticket_type(action["raw"])
        type_config = TICKET_TYPE_MAP[ticket_type]
        priority    = detect_priority(action["raw"] + " " + action.get("context", ""))
        assignees   = extract_assignees(action["assignee_hint"])
        due_date    = parse_due_date(action["due_hint"])

        tickets.append({
            "ticket_id":    f"AUTO-{str(i).zfill(3)}",
            "summary":      action["raw"],
            "issue_type":   type_config["issue_type"],
            "priority":     priority,
            "status":       "To Do",
            "assignees":    assignees,
            "due_date":     due_date,
            "context":      action.get("context", ""),
            "labels":       ["auto-generated", "sprint-planning", "meeting-2026-03-14"],
            "source":       "Sprint Planning + Product Review — March 14 2026",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    return tickets


def save_json(tickets: list, path: str) -> None:
    output = {
        "pipeline_version":  "1.1",
        "source_transcript": TRANSCRIPT_FILE,
        "generated_at":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_tickets":     len(tickets),
        "tickets":           tickets,
    }
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  JSON saved   : {path} ({len(tickets)} tickets)")


def save_chart(tickets: list, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    priorities = [t["priority"] for t in tickets]
    types      = [t["issue_type"] for t in tickets]
    assignees  = [
        t["assignees"][0]["name"] if len(t["assignees"]) == 1 else "Sarah + James"
        for t in tickets
    ]
    row_data = [
        [
            t["ticket_id"],
            t["issue_type"],
            t["priority"],
            t["due_date"],
            t["assignees"][0]["name"] if len(t["assignees"]) == 1 else "Sarah + James",
        ]
        for t in tickets
    ]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(
        "Meeting to Jira Pipeline Output\nSprint Planning + Product Review — March 14, 2026",
        fontsize=13, fontweight="bold", y=1.02,
    )

    ax1 = axes[0]
    ax1.axis("off")
    table = ax1.table(
        cellText=row_data,
        colLabels=["ID", "Type", "Priority", "Due Date", "Assignee"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.6)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#e0e0e0")
        if row == 0:
            cell.set_facecolor("#003314")
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f7f7f7")
        else:
            cell.set_facecolor("white")
        if row > 0 and col == 2:
            p = row_data[row - 1][2]
            cell.set_facecolor(PRIORITY_COLORS[p])
            cell.set_text_props(
                color="white" if p == "High" else "#003314",
                fontweight="bold",
            )
    ax1.set_title("Generated Tickets", fontsize=11, fontweight="bold", pad=12)

    axes[1].axis("off")
    ax_pri  = fig.add_axes([0.55, 0.55, 0.2,  0.35])
    ax_type = fig.add_axes([0.78, 0.55, 0.2,  0.35])
    ax_asgn = fig.add_axes([0.55, 0.08, 0.43, 0.38])

    pri_counts = {k: priorities.count(k) for k in ["High", "Medium", "Low"] if priorities.count(k)}
    ax_pri.pie(
        list(pri_counts.values()),
        labels=[f"{k}\n({v})" for k, v in pri_counts.items()],
        colors=[PRIORITY_COLORS[k] for k in pri_counts],
        textprops={"fontsize": 8},
        startangle=90,
    )
    ax_pri.set_title("Priority", fontsize=9, fontweight="bold")

    type_counts = Counter(types)
    ax_type.pie(
        list(type_counts.values()),
        labels=[f"{k}\n({v})" for k, v in type_counts.items()],
        colors=[TYPE_COLORS.get(k, "#aaa") for k in type_counts],
        textprops={"fontsize": 8},
        startangle=90,
    )
    ax_type.set_title("Type", fontsize=9, fontweight="bold")

    asgn_counts = Counter(assignees)
    ax_asgn.barh(list(asgn_counts.keys()), list(asgn_counts.values()), color="#003314", height=0.5)
    ax_asgn.set_title("Tickets per Assignee", fontsize=9, fontweight="bold")
    ax_asgn.set_xlabel("# Tickets", fontsize=8)
    ax_asgn.tick_params(labelsize=8)
    ax_asgn.spines["top"].set_visible(False)
    ax_asgn.spines["right"].set_visible(False)
    for i, (k, v) in enumerate(asgn_counts.items()):
        ax_asgn.text(v + 0.05, i, str(v), va="center", fontsize=8,
                     color="#003314", fontweight="bold")

    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Chart saved  : {path}")


def print_summary(tickets: list) -> None:
    print(f"\n{'ID':<12} {'Type':<10} {'Priority':<10} {'Due':<14} {'Assignee':<22} Summary")
    print("-" * 100)
    for t in tickets:
        assignee = t["assignees"][0]["name"] if len(t["assignees"]) == 1 else "Sarah + James"
        summary  = t["summary"][:45] + "..." if len(t["summary"]) > 45 else t["summary"]
        print(f"{t['ticket_id']:<12} {t['issue_type']:<10} {t['priority']:<10} "
              f"{t['due_date']:<14} {assignee:<22} {summary}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mode = "parsed"
    if "--mode" in sys.argv:
        idx  = sys.argv.index("--mode")
        mode = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "parsed"

    print("=" * 55)
    print("  MEETING TO JIRA PIPELINE")
    print("=" * 55)
    print(f"\n  Mode         : {mode}")
    print(f"  Transcript   : {TRANSCRIPT_FILE}\n")

    if mode == "hardcoded":
        print("  Using curated action list.\n")
        actions = CURATED_ACTIONS
    else:
        print("  Parsing transcript directly...\n")
        actions = parse_transcript(TRANSCRIPT_FILE)

        if not actions:
            print("  Parser returned no results. Falling back to curated list.\n")
            actions = CURATED_ACTIONS
        else:
            validation = validate_extraction(actions, expected_count=8)
            print(f"  Extraction validation:")
            print(f"    Items extracted : {validation['extracted']}")
            print(f"    Expected        : {validation['expected']}")
            print(f"    Match rate      : {validation['match_rate']}%")
            print(f"    Status          : {validation['status']}\n")

    tickets = build_tickets(actions)

    print(f"  Tickets generated: {len(tickets)}")
    save_json(tickets, OUTPUT_JSON)
    save_chart(tickets, OUTPUT_CHART)
    print_summary(tickets)

    print("\n" + "=" * 55)
