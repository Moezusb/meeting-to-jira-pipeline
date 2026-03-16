# PROJECT ORACLE V2: REVENUE-AWARE ACTION ENGINE

**Converts raw meeting transcripts into validated, revenue-prioritized Jira tickets.**

---

## THE PROBLEM

Standard meeting summaries fail because they strip business context. A bug flagged in a sprint call might be classified as "Medium" priority technically -- but if it is actively blocking a $120k enterprise client from running their weekly reports, it is "Highest" priority strategically.

Project Oracle V2 bridges the gap between the meeting room and the engineering backlog by adding a **Revenue Intelligence Gate** to the extraction pipeline.

---

## WHAT IT DOES

1. **Parses** a raw meeting transcript and locates the ACTION ITEMS RECAP section
2. **Classifies** each action item by Jira issue type (Bug / Task / Story) and base priority
3. **Enriches** every ticket against a Revenue Bridge database of high-value clients
4. **Escalates** priority to `Highest` for any At-Risk client mention -- autonomously, with no manual triage
5. **Validates** all tickets against a Pydantic schema before export, reducing Jira sync failures to 0%
6. **Outputs** production-ready JSON and a three-panel strategic dashboard

---

## ARCHITECTURE

```
meeting_transcript.txt
        |
        v
transcript_parser.py       <- Rule-based extraction layer
        |                     (In production: replaced by Claude API call)
        v
pipeline_v2.py             <- Classification + Revenue Intelligence Gate
        |
        +-- high_value_clients.json   <- Revenue Bridge (CRM export)
        |
        v
models.py                  <- Pydantic schema enforcement
        |
        v
jira_v2_production_ready.json
        |
        v
v2_dashboard.py            <- Strategic visualization
        |
        v
outputs/v2_strategic_summary.png
```

---

## REVENUE INTELLIGENCE GATE

The key differentiator in V2. After base classification, the pipeline scans each ticket's content against a High-Value Client database:

| Client Status | Action |
|:---|:---|
| **At-Risk** | Priority overridden to `Highest`, label `REVENUE-AT-RISK` added |
| **Watch** | Priority raised to `High` if not already escalated |
| **Healthy** | No change |

This mirrors how an experienced operations lead would actually read the room -- the same bug that is "Medium" for a healthy client becomes a drop-everything issue when it is blocking a client already showing churn signals.

---

## SAMPLE OUTPUT

```
ID         Priority   Type     Assignee               Due          Summary
------------------------------------------------------------------------------------------
AUTO-001   Medium     Bug      james                  2026-03-18   Fix CSV export truncation bug
AUTO-002   Medium     Task     priya                  2026-03-19   Regression testing on export module
AUTO-003   Highest    Task     tom                    2026-03-14   Send holding message to Harlow Logistics [REVENUE]
AUTO-004   Story      Story    aisha                  2026-03-20   Finalize onboarding designs
AUTO-005   Low        Task     tom + sarah            2026-03-21   Build Confluence auto-population automation
AUTO-006   Low        Task     james + sarah          2026-03-28   Spec Zendesk-to-Jira severity integration
AUTO-007   Medium     Task     james                  2026-03-16   Technical changelog for v2.4
AUTO-008   Medium     Task     sarah                  2026-03-17   Client-facing release notes
```

Revenue escalations: 1 (AUTO-003 -- Harlow Logistics, $120k ARR, At-Risk)

---

## HOW TO RUN

**GitHub Codespaces (recommended)**

```bash
pip install -r requirements.txt
python pipeline_v2.py
python v2_dashboard.py
```

**Google Colab**

```python
!pip install -r requirements.txt
!python pipeline_v2.py
!python v2_dashboard.py
from IPython.display import Image
Image("outputs/v2_strategic_summary.png")
```

Output: `outputs/v2_strategic_summary.png`

---

## DESIGN DECISIONS

**Why rule-based extraction instead of an API call?**
The `transcript_parser.py` module is an explicit demonstration of the extraction logic that a production LLM call would replace. It makes the architecture legible without requiring an API key to run. The comment in the code makes this tradeoff explicit.

**Why Pydantic for schema enforcement?**
Jira's API rejects tickets that fail field validation with no useful error. Running validation before export surfaces issues at the Python layer, where they are debuggable. Zero schema failures in the output file means zero sync failures in production.

**Why a Revenue Bridge instead of just keyword escalation?**
Hardcoded keywords like "Harlow" would work once and break the moment a client is renamed or a new at-risk account is added. Pulling from a structured client database means the escalation logic updates automatically when the CRM does.

**Why separate pipeline and dashboard scripts?**
Separation of concerns. The pipeline can run headless in CI. The dashboard is an optional reporting layer that consumes the JSON output independently.

---

## WHAT I WOULD BUILD NEXT

- Replace `transcript_parser.py` with a Claude API call that handles transcripts without a formal recap section
- Pull `high_value_clients.json` from a live CRM export (Salesforce / HubSpot)
- Add a Jira API integration to push validated tickets directly rather than exporting JSON
- Slack notification on any `REVENUE-AT-RISK` escalation

---

**Stack:** Python, Pydantic, Matplotlib, Pandas, JSON  
**Author:** Mohamed Bah  
**Status:** Production-grade pipeline, Codespaces-ready
