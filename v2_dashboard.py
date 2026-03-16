"""
v2_dashboard.py
===============
Generates the Project Oracle V2 strategic visualization.
Reads from jira_v2_production_ready.json and produces
a three-panel dashboard saved to outputs/v2_strategic_summary.png

Run after pipeline_v2.py:
    python v2_dashboard.py

Author: Mohamed Bah
"""

import json
import os
import matplotlib.pyplot as plt
import pandas as pd


# ─────────────────────────────────────────────
# COLOUR PALETTE (matches portfolio site)
# ─────────────────────────────────────────────

FOREST_GREEN   = "#2d5a27"
MID_GREEN      = "#4a7c40"
LIGHT_GREEN    = "#6b9e7e"
REVENUE_RED    = "#b30000"
LIGHT_RED      = "#d94f4f"
BG_DARK        = "#1a1a1a"
TEXT_LIGHT     = "#f0f0f0"
TEXT_MID       = "#aaaaaa"
GRID_LINE      = "#333333"


def load_tickets(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found.\n"
            "Run 'python pipeline_v2.py' first to generate the source data."
        )
    with open(path, "r") as f:
        data = json.load(f)
    return pd.DataFrame(data["tickets"])


def build_dashboard(df: pd.DataFrame, output_path: str) -> None:
    plt.rcParams.update({
        "figure.facecolor":  BG_DARK,
        "axes.facecolor":    BG_DARK,
        "axes.edgecolor":    GRID_LINE,
        "axes.labelcolor":   TEXT_LIGHT,
        "xtick.color":       TEXT_MID,
        "ytick.color":       TEXT_MID,
        "text.color":        TEXT_LIGHT,
        "grid.color":        GRID_LINE,
        "font.family":       "sans-serif",
    })

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.patch.set_facecolor(BG_DARK)
    fig.suptitle(
        "PROJECT ORACLE V2 -- STRATEGIC WORKLOAD ANALYSIS",
        fontsize=14,
        fontweight="bold",
        color=TEXT_LIGHT,
        y=1.02,
    )

    # ── CHART 1: Tickets by Priority ──────────────────────────
    ax1 = axes[0]
    priority_order = ["Highest", "High", "Medium", "Low"]

    df["priority"] = pd.Categorical(df["priority"], categories=priority_order, ordered=True)
    priority_counts = df["priority"].value_counts().reindex(priority_order, fill_value=0)

    bar_colors = [
        REVENUE_RED  if p == "Highest" else
        LIGHT_RED    if p == "High"    else
        FOREST_GREEN if p == "Medium"  else
        LIGHT_GREEN
        for p in priority_order
    ]

    bars = ax1.bar(priority_counts.index, priority_counts.values, color=bar_colors, width=0.6)
    ax1.set_title("Tickets by Priority", fontsize=11, color=TEXT_LIGHT, pad=10)
    ax1.set_ylabel("Count", color=TEXT_MID, fontsize=9)
    ax1.set_ylim(0, priority_counts.max() + 1.5)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.set_axisbelow(True)

    for bar, val in zip(bars, priority_counts.values):
        if val > 0:
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                str(val),
                ha="center", va="bottom",
                color=TEXT_LIGHT, fontsize=10, fontweight="bold",
            )

    # ── CHART 2: Revenue Risk vs Standard Ops (pie) ───────────
    ax2 = axes[1]
    revenue_count  = int(df["revenue_risk"].sum())
    standard_count = len(df) - revenue_count

    # Only include segments that actually have tickets
    sizes  = []
    labels = []
    colors = []

    if revenue_count > 0:
        sizes.append(revenue_count)
        labels.append(f"Revenue Protection\n({revenue_count} ticket{'s' if revenue_count != 1 else ''})")
        colors.append(REVENUE_RED)

    if standard_count > 0:
        sizes.append(standard_count)
        labels.append(f"Standard Ops\n({standard_count} ticket{'s' if standard_count != 1 else ''})")
        colors.append(FOREST_GREEN)

    explode = [0.08] + [0] * (len(sizes) - 1) if len(sizes) > 1 else [0]

    ax2.pie(
        sizes,
        labels=labels,
        autopct="%1.0f%%" if len(sizes) > 1 else None,
        colors=colors,
        startangle=140,
        explode=explode,
        textprops={"color": TEXT_LIGHT, "fontsize": 9},
        wedgeprops={"linewidth": 1.5, "edgecolor": BG_DARK},
    )
    ax2.set_title("Churn Mitigation Impact", fontsize=11, color=TEXT_LIGHT, pad=10)

    # ── CHART 3: Tickets by Assignee ──────────────────────────
    ax3 = axes[2]

    # Flatten multi-assignee tickets
    assignee_counts: dict = {}
    for _, row in df.iterrows():
        for person in row["assignees"]:
            name = person["name"].strip().title()
            assignee_counts[name] = assignee_counts.get(name, 0) + 1

    if assignee_counts:
        sorted_assignees = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)
        names, counts = zip(*sorted_assignees)

        # Color each assignee bar red if they own any revenue-flagged ticket
        def assignee_has_revenue(name: str) -> bool:
            return df[df["assignees"].apply(
                lambda a: any(p["name"].strip().title() == name for p in a)
            )]["revenue_risk"].any()

        bar_colors_3 = [
            REVENUE_RED if assignee_has_revenue(n) else FOREST_GREEN
            for n in names
        ]

        hbars = ax3.barh(names, counts, color=bar_colors_3, height=0.55)
        ax3.set_title("Workload by Assignee", fontsize=11, color=TEXT_LIGHT, pad=10)
        ax3.set_xlabel("Tickets Assigned", color=TEXT_MID, fontsize=9)
        ax3.set_xlim(0, max(counts) + 1.5)
        ax3.grid(axis="x", linestyle="--", alpha=0.4)
        ax3.set_axisbelow(True)
        ax3.invert_yaxis()

        for bar, val in zip(hbars, counts):
            ax3.text(
                bar.get_width() + 0.08,
                bar.get_y() + bar.get_height() / 2,
                str(val),
                va="center", color=TEXT_LIGHT, fontsize=10, fontweight="bold",
            )

    # ── Save ──────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"Dashboard saved to {output_path}")


if __name__ == "__main__":
    INPUT_PATH  = "jira_v2_production_ready.json"
    OUTPUT_PATH = "outputs/v2_strategic_summary.png"

    print("Loading pipeline output...")
    df = load_tickets(INPUT_PATH)
    print(f"  {len(df)} tickets loaded.")

    print("Generating dashboard...")
    build_dashboard(df, OUTPUT_PATH)
    print("Done.")
