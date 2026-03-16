import json
import pandas as pd
from datetime import datetime
from models import JiraTicket

# MBA LOGIC: Cross-reference with our "Revenue Bridge" high-risk list
# In production, this would pull from your revenue_analysis.py output
AT_RISK_CLIENTS = ["Harlow Logistics", "Meridian Technologies", "Northgate Financial"]

def enrich_with_revenue_intelligence(ticket_data):
    """
    MBA Move: Automatically escalates priority if a high-value 
    client from the Revenue Bridge is mentioned.
    """
    is_at_risk = any(client.lower() in ticket_data['context'].lower() for client in AT_RISK_CLIENTS)
    
    if is_at_risk:
        ticket_data['priority'] = "Highest"
        ticket_data['labels'].append("REVENUE-AT-RISK")
        ticket_data['revenue_risk'] = True
    
    return ticket_data

def process_pipeline():
    # 1. Load your existing JSON output (simulating the ingestion)
    with open('jira_tickets_output.json', 'r') as f:
        data = json.load(f)
    
    v2_tickets = []
    
    for raw_ticket in data['tickets']:
        # 2. Enrich with Revenue Intelligence
        enriched_data = enrich_with_revenue_intelligence(raw_ticket)
        
        # 3. Schema Enforcement (Pydantic validation)
        # This ensures the data is "clean" before it ever hits Jira
        try:
            validated_ticket = JiraTicket(**enriched_data)
            v2_tickets.append(validated_ticket.model_dump())
        except Exception as e:
            print(f"Validation Error for {raw_ticket['ticket_id']}: {e}")

    # 4. Save the "Production-Ready" Output
    with open('jira_v2_production_ready.json', 'w') as f:
        json.dump(v2_tickets, f, indent=2)
    
    print(f"✅ V2 Pipeline Complete: {len(v2_tickets)} tickets validated.")
    print(f"🔥 Revenue Risks Identified: {sum(1 for t in v2_tickets if t['revenue_risk'])}")

if __name__ == "__main__":
    process_pipeline()
