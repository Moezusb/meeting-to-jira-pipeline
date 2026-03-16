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
    # MBA FIX: Check if the source file exists. If not, run the original parser logic.
    source_file = 'jira_tickets_output.json'
    
    if not os.path.exists(source_file):
        print(f"⚠️ {source_file} not found. Running original pipeline to generate source data...")
        from pipeline import build_tickets
        from transcript_parser import parse_transcript
        actions = parse_transcript('meeting_transcript.txt')
        tickets_to_process = build_tickets(actions)
    else:
        with open(source_file, 'r') as f:
            data = json.load(f)
            tickets_to_process = data['tickets']
    
    v2_tickets = []
    
    for raw_ticket in tickets_to_process:
        # Enrich with Revenue Intelligence
        enriched_data = enrich_with_revenue_intelligence(raw_ticket)
        
        # Schema Enforcement
        try:
            validated_ticket = JiraTicket(**enriched_data)
            v2_tickets.append(validated_ticket.model_dump())
        except Exception as e:
            print(f"Validation Error: {e}")

    # Save the "Production-Ready" Output
    with open('jira_v2_production_ready.json', 'w') as f:
        json.dump(v2_tickets, f, indent=2)
    
    print(f"✅ V2 Pipeline Complete: {len(v2_tickets)} tickets validated.")

if __name__ == "__main__":
    process_pipeline()
