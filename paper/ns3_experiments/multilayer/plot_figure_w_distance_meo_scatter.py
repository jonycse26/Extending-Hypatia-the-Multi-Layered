#!/usr/bin/env python3
"""
Figure W — Scatter: representative distance (km) vs. MEO usage ratio (experiment 3)

Generalizes the Figure V MEO bar idea onto a numeric distance axis so extra tiers/pairs can be
appended later without relayouting bars.

  x-axis: approximate great-circle distance (km) for each tier (defaults match README pair blurbs:
          short ≈ 2,800 km, medium ≈ 4,500 km, long ≈ 11,000 km — override with ``--tier-km``).
  y-axis: ``meo_usage_ratio`` (one point per multilayer TCP pair), same resolution order as Figure V:
          ``example_3_distance_scenario_results.csv`` first, then ``multilayer_all_experiments_metrics.csv``.

Output: ``figure-w distance meo scatter/figure_w_distance_meo_scatter.{png,pdf}``.
"""

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-w distance meo scatter")
DEFAULT_SCENARIO_CSV = os.path.join(SCRIPT_DIR, "example_3_distance_scenario_results.csv")
DEFAULT_METRICS_CSV = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment3_distance_tiers,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)

import plot_figure_u_distance_tier_boxplots as figu


def _to_float(v):
    try:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return float("nan")
        return float(v)
    except Exception:
        return float("nan")


def _meo_for_tier(scenario_row, metrics_by_run, run_name_fallback=None):
    if scenario_row:
        v = _to_float(scenario_row.get("meo_usage_ratio"))
        if v == v:
            return v
        rn = (scenario_row.get("run_name") or "").strip()
        if rn and rn in metrics_by_run:
            v = _to_float(metrics_by_run[rn].get("meo_usage_ratio"))
            if v == v:
                return v
    if run_name_fallback and run_name_fallback in metrics_by_run:
        v = _to_float(metrics_by_run[run_name_fallback].get("meo_usage_ratio"))
        if v == v:
            return v
    return float("nan")


def _short_pair_label(pair_field):
    if not pair_field:
        return ""
    s = str(pair_field)
    if "(" in s:
        s = s.split("(", 1)[0].strip()
    return s.replace("distance", "").strip()


def _parse_tier_km(s):
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) != len(experiment3_distance_tiers):
        raise ValueError(
            "expected %d comma-separated km values (short,medium,long), got %d in %r"
            % (len(experiment3_distance_tiers), len(parts), s)
        )
    return [float(p) for p in parts]


def main():
    ap = argparse.ArgumentParser(description="Figure W: distance (km) vs MEO usage scatter.")
    ap.add_argument("--scenario-csv", default=DEFAULT_SCENARIO_CSV)
    ap.add_argument("--metrics-csv", default=DEFAULT_METRICS_CSV)
    ap.add_argument(
        "--tier-km",
        default="2800,4500,11000",
        help="Comma-separated km for short,medium,long (must match tier count).",
    )
    ap.add_argument(
        "--out-prefix",
        default=None,
        help="Output path without extension.",
    )
    ap.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Footer annotation only.",
    )
    ap.add_argument(
        "--no-trend",
        action="store_true",
        help="Do not draw a light trend polyline through points in tier order.",
    )
    args = ap.parse_args()

    try:
        tier_km = _parse_tier_km(args.tier_km)
    except ValueError as e:
        print("ERROR:", e)
        return 1

    scenario_by_tier = figu._load_scenario_by_tier(args.scenario_csv)
    metrics_by_run = figu._load_metrics_rows(args.metrics_csv)
    tier_run = figu._tier_run_names_multilayer(scenario_by_tier)
    if len(tier_run) != len(tier_km):
        print(
            "ERROR: got %d tier runs but %d km values (check scenario / run_list vs --tier-km)."
            % (len(tier_run), len(tier_km))
        )
        return 1

    xs, ys, labels = [], [], []
    for (tier, rn), km in zip(tier_run, tier_km):
        row = scenario_by_tier.get(tier)
        y = _meo_for_tier(row, metrics_by_run, run_name_fallback=rn)
        if y != y:
            continue
        xs.append(km)
        ys.append(y)
        lab = ""
        if row and row.get("pair"):
            lab = _short_pair_label(row.get("pair"))
        else:
            lab = tier.capitalize()
        labels.append(lab)

    if not xs:
        print("ERROR: no MEO values (check %s and %s)" % (args.scenario_csv, args.metrics_csv))
        return 1

    fig, ax = plt.subplots(figsize=(6.8, 4.6), layout="constrained")
    ax.scatter(
        xs,
        ys,
        s=140,
        c="#2ca02c",
        edgecolors="#1b5e20",
        linewidths=0.9,
        zorder=3,
        label="Multilayer",
    )

    order = np.argsort(xs)
    if not args.no_trend and len(xs) >= 2:
        ax.plot(
            np.asarray(xs)[order],
            np.asarray(ys)[order],
            color="#888888",
            linestyle="--",
            linewidth=1.1,
            alpha=0.85,
            zorder=2,
            label="Tier order",
        )

    xmax = max(xs)
    for km, y, lab in zip(xs, ys, labels):
        text = lab if lab else "%.0f km" % km
        near_right = xmax > 0 and km >= 0.92 * xmax
        if near_right:
            ax.annotate(
                text,
                (km, y),
                textcoords="offset points",
                xytext=(-10, 8),
                fontsize=8,
                color="#222222",
                ha="right",
                va="bottom",
            )
        else:
            ax.annotate(
                text,
                (km, y),
                textcoords="offset points",
                xytext=(6, 8),
                fontsize=8,
                color="#222222",
                ha="left",
                va="bottom",
            )

    ax.set_xlabel("Representative distance (km)", fontsize=11)
    ax.set_ylabel("MEO usage ratio", fontsize=11)
    ax.set_title("Distance vs. MEO usage (multilayer tiers)", fontsize=12)
    ax.set_ylim(-0.02, max(0.08, max(ys) * 1.2))
    ax.set_xlim(0.0, xmax * 1.06 if xmax > 0 else 1.0)
    ax.grid(True, linestyle=":", alpha=0.55)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)

    out_prefix = args.out_prefix or os.path.join(OUT_DIR, "figure_w_distance_meo_scatter")
    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    print("Figure W: %d points · sim length %d s (paper default)" % (len(xs), simulation_end_time_s))
    print("Wrote:", png)
    print("Wrote:", pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
