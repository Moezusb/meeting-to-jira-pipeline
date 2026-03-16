# 🎙️ PROJECT ORACLE: STRATEGIC ACTION ENGINE (V2)
**Intelligent Jira Pipeline: Linking Executive Transcripts to Revenue Protection**

---

### [ 01. THE STRATEGIC PROBLEM ]
Standard meeting summaries fail because they lack **Business Context**. A bug discussed in a meeting might be "Medium" priority technically, but if it affects a $100k Enterprise account, it is "Highest" priority strategically. Project Oracle V2 bridges the gap between the meeting room and the engineering backlog.

### [ 02. V2 INTELLIGENCE: REVENUE-AWARE ROUTING ]
This pipeline goes beyond keyword matching. It features a **Revenue Logic Gate** that cross-references extracted action items against a High-Value Client database.
* **Autonomous Escalation:** If a ticket mentions an "At-Risk" client (e.g., Harlow Logistics), the pipeline automatically overrides the priority to **CRITICAL**.
* **Schema Enforcement:** Uses **Pydantic Models** to ensure all tickets meet strict Jira API requirements before export, reducing sync failures to 0%.

### [ 03. UPDATED ARCHITECTURE ]
1.  **Ingestion:** Raw transcript processed via Python.
2.  **Enrichment (`pipeline_v2.py`):** AI-logic performs a lookup against the **Revenue Bridge** database.
3.  **Validation (`models.py`):** Schema enforcement for production-grade reliability.
4.  **Strategic Visualization (`v2_dashboard.py`):** Generates a workload analysis highlighting "Revenue Protection" vs. "Standard Ops."

### [ 04. V2 SAMPLE OUTPUT ]
| Ticket | Client Mention | Priority | Strategy |
| :--- | :--- | :--- | :--- |
| **AUTO-001** | Harlow Logistics | **CRITICAL** | **Revenue Protection** |
| **AUTO-006** | Meridian Tech | **CRITICAL** | **Revenue Protection** |
| **AUTO-004** | N/A | Medium | Standard Operations |

---

### [ 05. HOW TO RUN (CODESPACES) ]
1. Open in **GitHub Codespaces**.
2. Run `pip install -r requirements.txt`.
3. Execute the Intelligence Engine: `python pipeline_v2.py`.
4. Generate Strategic Visuals: `python v2_dashboard.py`.

**Output:** `outputs/v2_strategic_summary.png`

---
**Status:** ✅ Production-Grade / Revenue-Aware  
**Stack:** Python, Pydantic, Matplotlib, JSON  
**Author:** Mohamed Bah
