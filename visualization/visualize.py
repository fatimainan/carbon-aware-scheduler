"""
visualization/visualize.py
────────────────────────────────────────────────────────────────────────────────
Phase 2 — Visualization & Analysis

Generates MANDATORY graphs from the execution log:
  Graph 1 — Carbon intensity over time (with threshold line)
  Graph 2 — Execute vs Delay decision distribution
  Graph 3 — Carbon intensity distribution by decision type  (bonus)

Also prints a structured textual analysis to stdout.

Usage
-----
    python visualization/visualize.py                     # uses default log
    python visualization/visualize.py --log logs/my.csv  # custom log
    python visualization/visualize.py --no-show           # save only, no popup
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # headless — works without a display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import LOG_FILE_CSV, CARBON_THRESHOLD

# ── Colour palette ────────────────────────────────────────────────────────────
C_EXECUTE  = "#2ecc71"   # green
C_DELAY    = "#e74c3c"   # red
C_THRESH   = "#e67e22"   # orange
C_CARBON   = "#3498db"   # blue
C_BG       = "#f8f9fa"

OUTPUT_DIR = Path("visualization/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data loader ───────────────────────────────────────────────────────────────

def load_log(path: str = LOG_FILE_CSV) -> list[dict]:
    """Parse CSV log into a list of record dicts."""
    records = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                records.append({
                    "timestamp":        datetime.fromisoformat(row["timestamp"]),
                    "carbon_intensity": float(row["carbon_intensity"]),
                    "threshold":        float(row["threshold"]),
                    "decision":         row["decision"],
                    "execution_status": row["execution_status"],
                    "zone":             row.get("zone", "?"),
                })
            except (ValueError, KeyError):
                continue
    return records


# ── Graph 1 — Carbon intensity over time ─────────────────────────────────────

def graph_carbon_over_time(records: list[dict], save: bool = True) -> str:
    times      = [r["timestamp"] for r in records]
    intensities = [r["carbon_intensity"] for r in records]
    thresholds  = [r["threshold"] for r in records]
    decisions   = [r["decision"] for r in records]

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)

    # Shade background by decision
    for i, (t, c, d) in enumerate(zip(times, intensities, decisions)):
        colour = C_EXECUTE if d == "execute" else C_DELAY
        ax.axvspan(
            mdates.date2num(t) - 0.002,
            mdates.date2num(t) + 0.002,
            alpha=0.15,
            color=colour,
            linewidth=0,
        )

    # Carbon line
    ax.plot(times, intensities, color=C_CARBON, linewidth=2.5,
            marker="o", markersize=7, zorder=5, label="Carbon intensity")

    # Scatter colour by decision
    for t, c, d in zip(times, intensities, decisions):
        ax.scatter(t, c,
                   color=C_EXECUTE if d == "execute" else C_DELAY,
                   s=80, zorder=6, edgecolors="white", linewidths=1)

    # Threshold line
    ax.axhline(
        thresholds[0], color=C_THRESH, linestyle="--", linewidth=1.8,
        label=f"Threshold = {thresholds[0]:.0f} gCO₂/kWh",
    )

    # Formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    plt.xticks(rotation=35, ha="right", fontsize=8)
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Carbon Intensity (gCO₂/kWh)", fontsize=11)
    ax.set_title("Carbon Intensity Over Time with Scheduler Decisions",
                 fontsize=13, fontweight="bold", pad=12)

    # Legend
    exec_patch  = mpatches.Patch(color=C_EXECUTE, label="EXECUTE")
    delay_patch = mpatches.Patch(color=C_DELAY,   label="DELAY")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles=handles + [exec_patch, delay_patch],
              loc="upper right", fontsize=9, framealpha=0.85)

    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()

    out = str(OUTPUT_DIR / "graph1_carbon_over_time.png")
    if save:
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"[Viz] Graph 1 saved → {out}")
    return out


# ── Graph 2 — Execute vs Delay pie / bar ─────────────────────────────────────

def graph_decision_distribution(records: list[dict], save: bool = True) -> str:
    counts = Counter(r["decision"] for r in records)
    execute_n = counts.get("execute", 0)
    delay_n   = counts.get("delay",   0)
    total     = execute_n + delay_n

    fig, (ax_pie, ax_bar) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(C_BG)
    for ax in (ax_pie, ax_bar):
        ax.set_facecolor(C_BG)

    # ── Pie chart ─────────────────────────────────────────────────────────────
    labels  = [f"EXECUTE\n({execute_n})", f"DELAY\n({delay_n})"]
    colors  = [C_EXECUTE, C_DELAY]
    explode = (0.05, 0.05)
    wedge_props = dict(linewidth=1.5, edgecolor="white")

    ax_pie.pie(
        [execute_n, delay_n],
        labels=labels,
        colors=colors,
        explode=explode,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=wedge_props,
        textprops={"fontsize": 11},
    )
    ax_pie.set_title("Decision Distribution", fontsize=12, fontweight="bold")

    # ── Bar chart by cycle ────────────────────────────────────────────────────
    cycles = list(range(1, len(records) + 1))
    bar_colors = [C_EXECUTE if r["decision"] == "execute" else C_DELAY
                  for r in records]
    intensities = [r["carbon_intensity"] for r in records]

    bars = ax_bar.bar(cycles, intensities, color=bar_colors,
                      edgecolor="white", linewidth=0.8, width=0.6)
    ax_bar.axhline(
        records[0]["threshold"],
        color=C_THRESH, linestyle="--", linewidth=2,
        label=f"Threshold = {records[0]['threshold']:.0f} gCO₂/kWh",
    )
    ax_bar.set_xlabel("Cycle #", fontsize=11)
    ax_bar.set_ylabel("Carbon Intensity (gCO₂/kWh)", fontsize=11)
    ax_bar.set_title("Carbon Intensity per Cycle (coloured by decision)",
                     fontsize=12, fontweight="bold")
    ax_bar.legend(fontsize=9, framealpha=0.85)
    ax_bar.grid(axis="y", linestyle=":", alpha=0.5)

    exec_patch  = mpatches.Patch(color=C_EXECUTE, label="EXECUTE")
    delay_patch = mpatches.Patch(color=C_DELAY,   label="DELAY")
    ax_bar.legend(handles=[exec_patch, delay_patch,
                            mpatches.Patch(color=C_THRESH, label="Threshold")],
                  loc="upper right", fontsize=9, framealpha=0.85)

    plt.tight_layout()
    out = str(OUTPUT_DIR / "graph2_decision_distribution.png")
    if save:
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"[Viz] Graph 2 saved → {out}")
    return out


# ── Graph 3 (bonus) — Distribution by decision type ──────────────────────────

def graph_intensity_boxplot(records: list[dict], save: bool = True) -> str:
    exec_vals  = [r["carbon_intensity"] for r in records if r["decision"] == "execute"]
    delay_vals = [r["carbon_intensity"] for r in records if r["decision"] == "delay"]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)

    data   = [v for v in [exec_vals, delay_vals] if v]
    labels = []
    colors = []
    if exec_vals:
        labels.append(f"EXECUTE\n(n={len(exec_vals)})")
        colors.append(C_EXECUTE)
    if delay_vals:
        labels.append(f"DELAY\n(n={len(delay_vals)})")
        colors.append(C_DELAY)

    bp = ax.boxplot(data, labels=labels, patch_artist=True,
                    widths=0.5, medianprops=dict(color="white", linewidth=2))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    threshold = records[0]["threshold"]
    ax.axhline(threshold, color=C_THRESH, linestyle="--", linewidth=1.8,
               label=f"Threshold = {threshold:.0f} gCO₂/kWh")

    ax.set_ylabel("Carbon Intensity (gCO₂/kWh)", fontsize=11)
    ax.set_title("Carbon Intensity Distribution by Decision Type",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9, framealpha=0.85)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()

    out = str(OUTPUT_DIR / "graph3_intensity_boxplot.png")
    if save:
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"[Viz] Graph 3 saved → {out}")
    return out


# ── Analysis report ───────────────────────────────────────────────────────────

def print_analysis(records: list[dict]) -> None:
    if not records:
        print("[Analysis] No records found.")
        return

    counts    = Counter(r["decision"] for r in records)
    total     = len(records)
    executed  = counts["execute"]
    delayed   = counts["delay"]
    threshold = records[0]["threshold"]

    intensities  = [r["carbon_intensity"] for r in records]
    avg_carbon   = sum(intensities) / total
    min_carbon   = min(intensities)
    max_carbon   = max(intensities)

    exec_vals  = [r["carbon_intensity"] for r in records if r["decision"] == "execute"]
    delay_vals = [r["carbon_intensity"] for r in records if r["decision"] == "delay"]
    avg_exec   = sum(exec_vals) / len(exec_vals)   if exec_vals  else 0
    avg_delay  = sum(delay_vals) / len(delay_vals) if delay_vals else 0

    avoidance_pct = (delayed / total * 100) if total else 0

    # Carbon savings estimate (rough: assume each delayed unit = avg_delay gCO2)
    carbon_saved = delayed * (avg_delay - threshold) if delayed and avg_delay > threshold else 0

    banner = "═" * 62

    print(f"\n{banner}")
    print("  ANALYSIS REPORT — Carbon-Aware Scheduling System")
    print(banner)
    print(f"  Threshold configured    : {threshold:.1f} gCO₂/kWh")
    print(f"  Total scheduling cycles : {total}")
    print(f"  Executed immediately    : {executed}  ({executed/total*100:.1f}%)")
    print(f"  Delayed                 : {delayed}  ({delayed/total*100:.1f}%)")
    print()
    print(f"  Carbon intensity stats:")
    print(f"    Overall average       : {avg_carbon:.1f} gCO₂/kWh")
    print(f"    Min / Max             : {min_carbon:.1f} / {max_carbon:.1f} gCO₂/kWh")
    print(f"    Avg when EXECUTED     : {avg_exec:.1f} gCO₂/kWh")
    print(f"    Avg when DELAYED      : {avg_delay:.1f} gCO₂/kWh")
    print()
    print(f"  Execution avoidance rate: {avoidance_pct:.1f}%")
    print(f"  Estimated carbon avoided: {carbon_saved:.0f} gCO₂ units")
    print()
    print("  KEY FINDINGS:")
    print()
    if avoidance_pct > 20:
        print("  ✅ The scheduler successfully reduced execution during high-")
        print("     carbon periods. A meaningful fraction of workloads were")
        print("     deferred, reducing real-time carbon emissions.")
    else:
        print("  ℹ️  Most cycles executed immediately, suggesting the observed")
        print("     carbon intensity was generally below the threshold during")
        print("     this run window.")

    print()
    if max_carbon > threshold * 1.5:
        print("  ✅ Several readings exceeded the threshold by >50%, indicating")
        print("     the threshold is well-calibrated for real peak periods.")
    else:
        print("  ℹ️  Carbon intensity never exceeded 1.5× the threshold.")
        print("     Consider lowering the threshold for more aggressive deferral.")

    print()
    gap = avg_delay - avg_exec
    if gap > 0:
        print(f"  ✅ Delayed jobs had on average {gap:.1f} gCO₂/kWh HIGHER intensity")
        print("     than executed ones — confirming the scheduler correctly")
        print("     identifies high-carbon execution windows.")
    print()
    print("  THRESHOLD EFFECTIVENESS:")
    print(f"  At {threshold:.0f} gCO₂/kWh the threshold catches {avoidance_pct:.1f}% of events.")
    if avoidance_pct < 15:
        print("  → Threshold may be too HIGH — most events slip through.")
    elif avoidance_pct > 60:
        print("  → Threshold may be too LOW — too many events are deferred.")
    else:
        print("  → Threshold appears well-balanced for this workload profile.")
    print(banner)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(log_path: str = LOG_FILE_CSV, show: bool = False) -> None:
    print(f"[Viz] Loading log: {log_path}")
    records = load_log(log_path)
    if not records:
        print(f"[Viz] ERROR: No valid records in {log_path}")
        return

    print(f"[Viz] Loaded {len(records)} records.")
    g1 = graph_carbon_over_time(records,      save=True)
    g2 = graph_decision_distribution(records, save=True)
    g3 = graph_intensity_boxplot(records,     save=True)
    print_analysis(records)

    print(f"\n[Viz] All graphs saved to: {OUTPUT_DIR}/")
    return g1, g2, g3


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Visualize carbon scheduler logs")
    p.add_argument("--log",      default=LOG_FILE_CSV, help="Path to CSV log")
    p.add_argument("--no-show",  action="store_true",  help="Don't display plots")
    args = p.parse_args()
    main(log_path=args.log, show=not args.no_show)
