"""
transcript_parser.py
====================
Extracts action items directly from a raw meeting transcript by locating
the ACTION ITEMS RECAP section and parsing each line into structured data.

This module demonstrates the extraction layer of the pipeline. In production,
this function would be replaced by a single Claude API call that handles
unstructured transcripts without a formal recap section.

Author : Mohamed Bah
"""

import re
from typing import Optional


# ─────────────────────────────────────────────
# KNOWN ATTENDEES
# Maps first names to assignee hint strings
# used by the classification engine.
# In production this would be inferred by the
# LLM from the transcript itself.
# ─────────────────────────────────────────────

KNOWN_ATTENDEES = {
    "james":  "james",
    "priya":  "priya",
    "tom":    "tom",
    "aisha":  "aisha",
    "sarah":  "sarah",
}

# Due date keywords the parser looks for
DUE_DATE_SIGNALS = {
    "today":       "today",
    "monday":      "monday",
    "tuesday":     "tuesday",
    "wednesday":   "wednesday",
    "thursday":    "thursday",
    "friday":      "friday",
    "next week":   "next week",
    "two weeks":   "two weeks",
    "this week":   "next week",
}


def extract_recap_section(transcript: str) -> Optional[str]:
    """
    Locates and returns the ACTION ITEMS RECAP section from a transcript.
    Returns None if no recap section is found.
    """
    patterns = [
        r"ACTION ITEMS RECAP[:\s]*\n(.*?)(?:\n---|\Z)",
        r"ACTION ITEMS[:\s]*\n(.*?)(?:\n---|\Z)",
        r"RECAP[:\s]*\n(.*?)(?:\n---|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, transcript, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def parse_assignee(line: str) -> str:
    """
    Extracts assignee hint from an action item line.
    Handles patterns like:
        - James: Fix the bug
        - Sarah + James: Spec the integration
        - Tom can you send...
    """
    line_lower = line.lower()

    # Check for joint assignments first (e.g. "Sarah + James")
    found = []
    for name in KNOWN_ATTENDEES:
        if name in line_lower:
            found.append(name)

    if len(found) >= 2:
        return " ".join(found)
    elif len(found) == 1:
        return found[0]
    return "unassigned"


def parse_due_hint(line: str) -> str:
    """
    Extracts a due date hint from an action item line.
    Returns the most specific signal found, defaulting to 'next week'.
    """
    line_lower = line.lower()
    for signal, hint in DUE_DATE_SIGNALS.items():
        if signal in line_lower:
            return hint
    return "next week"


def clean_action_text(line: str) -> str:
    """
    Strips leading bullets, dashes, assignee prefixes, and whitespace
    from an action item line to produce a clean summary.
    """
    # Remove leading bullets and dashes
    line = re.sub(r"^[\-\*\•]\s*", "", line.strip())

    # Remove "Name:" or "Name +" prefix patterns
    line = re.sub(
        r"^([A-Z][a-z]+\s*[\+&]?\s*[A-Z]?[a-z]*\s*):\s*",
        "",
        line
    )
    return line.strip()


def parse_transcript(transcript_path: str) -> list:
    """
    Main entry point. Reads a transcript file, locates the ACTION ITEMS
    RECAP section, and returns a list of structured action item dicts
    ready for the classification engine.

    Each dict contains:
        raw           -- cleaned action item text
        assignee_hint -- first name(s) of assigned person(s)
        due_hint      -- natural language due date signal
        context       -- the original raw line for traceability
    """
    with open(transcript_path, "r") as f:
        transcript = f.read()

    recap = extract_recap_section(transcript)

    if recap is None:
        print("  [parser] No ACTION ITEMS RECAP section found.")
        print("  [parser] In production, Claude API would parse the full transcript.")
        return []

    lines = [l.strip() for l in recap.splitlines() if l.strip()]
    action_items = []

    for line in lines:
        # Skip empty lines and section headers
        if not line or len(line) < 10:
            continue
        # Skip lines that look like headers rather than action items
        if line.isupper():
            continue

        raw           = clean_action_text(line)
        assignee_hint = parse_assignee(line)
        due_hint      = parse_due_hint(line)

        if raw:
            action_items.append({
                "raw":           raw,
                "assignee_hint": assignee_hint,
                "due_hint":      due_hint,
                "context":       f"Extracted from transcript recap: {line[:120]}",
            })

    return action_items


def validate_extraction(parsed: list, expected_count: int) -> dict:
    """
    Compares parsed action items against the expected count and
    returns a simple validation report.
    """
    extracted = len(parsed)
    match_rate = min(extracted / expected_count, 1.0) * 100 if expected_count > 0 else 0

    return {
        "expected":    expected_count,
        "extracted":   extracted,
        "match_rate":  round(match_rate, 1),
        "status":      "PASS" if match_rate >= 75 else "REVIEW",
    }


if __name__ == "__main__":
    # ── DEMO: run parser standalone ──
    import sys
    transcript_path = sys.argv[1] if len(sys.argv) > 1 else "meeting_transcript.txt"

    print(f"Parsing: {transcript_path}\n")
    items = parse_transcript(transcript_path)

    if items:
        validation = validate_extraction(items, expected_count=8)
        print(f"Extraction complete.")
        print(f"  Items extracted : {validation['extracted']}")
        print(f"  Expected        : {validation['expected']}")
        print(f"  Match rate      : {validation['match_rate']}%")
        print(f"  Status          : {validation['status']}\n")

        print(f"{'#':<4} {'Assignee':<18} {'Due':<12} Summary")
        print("-" * 80)
        for i, item in enumerate(items, 1):
            summary = item["raw"][:52] + "..." if len(item["raw"]) > 52 else item["raw"]
            print(f"{i:<4} {item['assignee_hint']:<18} {item['due_hint']:<12} {summary}")
    else:
        print("No action items extracted.")
        print("Ensure the transcript contains an ACTION ITEMS RECAP section.")
