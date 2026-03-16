import json
import matplotlib.pyplot as plt
import pandas as pd
import os

# 1. Load the Production-Ready Data
with open('jira_v2_production_ready.json', 'r') as f:
    tickets = json.load(f)

df = pd.DataFrame(tickets)

# 2. Setup the Visualization
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Project Oracle V2: Strategic Workload Analysis', fontsize=16, fontweight='bold')

# --- CHART 1: Workload by Priority (Highlighting Revenue Risk) ---
priority_order = ['Highest', 'High', 'Medium', 'Low']
df['priority'] = pd.Categorical(df['priority'], categories=priority_order, ordered=True)
priority_counts = df['priority'].value_counts().sort_index()

# Define colors: Highest (Revenue Risk) is deep red, others are forest green tones
colors = ['#b30000' if p == 'Highest' else '#2d5a27' for p in priority_order]

ax1.bar(priority_counts.index, priority_counts.values, color=colors)
ax1.set_title('Tickets by Priority Status', fontsize=12)
ax1.set_ylabel('Count')
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# --- CHART 2: Revenue Risk Distribution ---
risk_counts = df['revenue_risk'].value_counts()
labels = ['Standard Operations', 'Revenue Protection']
risk_colors = ['#6b9e7e', '#b30000']

ax2.pie(risk_counts, labels=labels, autopct='%1.1f%%', colors=risk_colors, startangle=140, explode=(0, 0.1))
ax2.set_title('Workload Impact on Churn Mitigation', fontsize=12)

# 3. Save the Output
os.makedirs('outputs', exist_ok=True)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig('outputs/v2_strategic_summary.png', dpi=150)
print("✅ V2 Strategic Dashboard generated in outputs/v2_strategic_summary.png")
