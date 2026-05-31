#!/usr/bin/env python3
"""
Hop-wise MEO usage (experiment 3 style) — satellite hop count vs. ``meo_usage_ratio``.

Pools valid fstate snapshots from multilayer TCP runs, buckets by satellite hop count
(2–5 by default), and plots ``N_MEO / N`` as a percentage (same definition as Figure V).

Routing policy (``meo_threshold_hops=3``): LEO-only paths with >3 LEO hops trigger MEO;
empirically, paths with 2–3 satellite hops rarely include MEO; 4–5 hops do.

Output: ``figure-v meo usage by hop/figure_v_meo_usage_by_hop.{png,pdf}``.
"""

import argparse
import glob
import os
import sys
import warnings

import matplotlib

warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-v meo usage by hop")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import dynamic_state_update_interval_ms, simulation_end_time_s
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)

import plot_figure_u_distance_tier_boxplots as figu
from evaluation_utils import (
    aggregate_meo_usage_by_hop,
    extract_hop_meo_snapshots,
)

DEFAULT_HOP_BINS = (2, 3, 4, 5)
MEO_PCT_PAD = 10.0


def _example3_multilayer_run_names(scenario_csv):
    scenario_by_tier = figu._load_scenario_by_tier(scenario_csv)
    return [rn for _tier, rn in figu._tier_run_names_multilayer(scenario_by_tier)]


def _all_multilayer_tcp_run_names():
    names = []
    for p in glob.glob(os.path.join(SCRIPT_DIR, "runs", "*_tcp")):
        if os.path.isdir(p):
            names.append(os.path.basename(p))
    return sorted(names)


def _pool_hop_meo_snapshots(run_names, metrics_duration_s, metrics_time_step_ms):
    all_snaps = []
    used_runs = []
    for rn in run_names:
        for rd in figu._run_dir_candidates(rn):
            if not os.path.isdir(rd):
                continue
            snaps = extract_hop_meo_snapshots(
                rd, None, metrics_duration_s, metrics_time_step_ms
            )
            if snaps:
                all_snaps.extend(snaps)
                used_runs.append(rn)
                break
    return all_snaps, used_runs


def _series_from_bins(hop_bins, agg):
    xs, ys, labels, ns = [], [], [], []
    for hop in hop_bins:
        row = agg.get(hop)
        if not row:
            continue
        xs.append(float(hop))
        ys.append(float(row["meo_usage_ratio"]))
        ns.append(int(row["n"]))
        labels.append("%d hops" % hop)
    return xs, ys, labels, ns


def _plot_meo_hop_scatter(
    ax, xs, ys, labels, ns, hop_bins, no_trend, title="(a) Hop count vs. MEO usage"
):
    if not xs:
        ax.text(0.5, 0.5, "no MEO data", ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_title(title, fontsize=11)
        return

    ys_pct = [100.0 * float(y) for y in ys]

    ax.scatter(
        xs,
        ys_pct,
        s=110,
        c="#2ca02c",
        edgecolors="#1b5e20",
        linewidths=0.85,
        zorder=3,
        label="Multilayer",
        clip_on=False,
    )
    order = np.argsort(xs)
    if not no_trend and len(xs) >= 2:
        ax.plot(
            np.asarray(xs)[order],
            np.asarray(ys_pct)[order],
            color="#888888",
            linestyle="--",
            linewidth=1.05,
            alpha=0.85,
            zorder=2,
            label="Hop order",
        )
    for hop, y, lab, n in zip(xs, ys_pct, labels, ns):
        text = "%s (n=%d)" % ((lab or "").strip() or "%.0f hops" % hop, n)
        if y <= 0.0:
            ax.annotate(
                text,
                (hop, y),
                textcoords="offset points",
                xytext=(0, 8),
                fontsize=7.5,
                color="#222222",
                ha="center",
                va="bottom",
            )
        elif y >= 100.0:
            # Below marker so labels do not cross the hop-order dashed line.
            ax.annotate(
                text,
                (hop, y),
                textcoords="offset points",
                xytext=(0, -12),
                fontsize=7.5,
                color="#222222",
                ha="center",
                va="top",
                zorder=4,
            )
        else:
            ax.annotate(
                text,
                (hop, y),
                textcoords="offset points",
                xytext=(6, 8),
                fontsize=7.5,
                color="#222222",
                ha="left",
                va="bottom",
            )

    ax.set_xlabel("Satellite hops", fontsize=9)
    ax.set_ylabel("MEO usage (%)", fontsize=9)
    ax.set_title(title, fontsize=11)
    y_lo = -MEO_PCT_PAD
    y_hi = 100.0 + MEO_PCT_PAD
    ax.set_ylim(y_lo, y_hi)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    hop_min = min(xs)
    hop_max = max(xs)
    ax.set_xlim(hop_min - 0.35, hop_max + 0.35)
    ax.set_xticks(hop_bins if hop_bins else list(DEFAULT_HOP_BINS))
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8, color="#888888", alpha=0.55, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=7, framealpha=0.92)
    frame_kw = dict(linewidth=1.0, color="#333333")
    for side in ("left", "right", "bottom", "top"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_zorder(10)
        for key, val in frame_kw.items():
            setattr(ax.spines[side], key, val)


def _write_csv(path, hop_bins, agg):
    import csv

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hop_count", "n_snapshots", "meo_usage_ratio", "meo_usage_pct"])
        for hop in hop_bins:
            row = agg.get(hop)
            if not row:
                continue
            r = row["meo_usage_ratio"]
            w.writerow([hop, row["n"], r, 100.0 * r])


def main():
    p = argparse.ArgumentParser(
        description="Hop-wise MEO usage scatter (multilayer fstate, Figure V styling)."
    )
    p.add_argument(
        "--scenario-csv",
        default=os.path.join(SCRIPT_DIR, "example_3_distance_scenario_results.csv"),
        help="Used with --example3-only to select the three multilayer distance runs.",
    )
    p.add_argument(
        "--example3-only",
        action="store_true",
        help="Only the three example-3 multilayer TCP runs (often only hop 5 has samples).",
    )
    p.add_argument(
        "--hop-bins",
        default="2,3,4,5",
        help="Comma-separated satellite hop counts to plot.",
    )
    p.add_argument("--no-trend", action="store_true", help="Do not draw hop-order dashed line.")
    p.add_argument("--out-prefix", default=None, help="Output path without extension.")
    p.add_argument(
        "--duration-s",
        type=float,
        default=float(simulation_end_time_s),
        help="fstate window (default: run_list.simulation_end_time_s).",
    )
    p.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="fstate step (default: run_list.dynamic_state_update_interval_ms).",
    )
    p.add_argument("--csv-out", default=None, help="Optional CSV path for aggregated bins.")
    args = p.parse_args()

    try:
        hop_bins = tuple(int(x.strip()) for x in args.hop_bins.split(",") if x.strip())
    except ValueError:
        print("ERROR: invalid --hop-bins %r" % args.hop_bins)
        return 1

    if args.example3_only:
        run_names = _example3_multilayer_run_names(args.scenario_csv)
    else:
        run_names = _all_multilayer_tcp_run_names()

    dur = float(args.duration_s)
    step_ms = int(args.time_step_ms)
    snapshots, used_runs = _pool_hop_meo_snapshots(run_names, dur, step_ms)
    if not snapshots:
        print("ERROR: no fstate snapshots (check runs/ and dynamic_state_%dms_for_%.0fs)" % (step_ms, dur))
        return 1

    agg = aggregate_meo_usage_by_hop(snapshots, hop_bins=hop_bins)
    xs, ys, labels, ns = _series_from_bins(hop_bins, agg)
    if not xs:
        print("ERROR: no samples in hop bins %s (total snapshots: %d)" % (hop_bins, len(snapshots)))
        return 1

    out_prefix = args.out_prefix or os.path.join(FIGURE_DIR, "figure_v_meo_usage_by_hop")
    csv_out = args.csv_out or os.path.join(FIGURE_DIR, "figure_v_meo_usage_by_hop.csv")

    fig, ax = plt.subplots(figsize=(5.8, 3.15), layout="constrained")
    _plot_meo_hop_scatter(ax, xs, ys, labels, ns, hop_bins, args.no_trend)

    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(csv_out)), exist_ok=True)
    _write_csv(csv_out, hop_bins, agg)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)

    print(
        "MEO by hop: %d runs · %d snapshots · dynamic_state_%dms_for_%.0fs"
        % (len(used_runs), len(snapshots), step_ms, dur)
    )
    for hop in hop_bins:
        row = agg.get(hop)
        if row:
            print("  hop %d: n=%d  meo_usage=%.1f%%" % (hop, row["n"], 100.0 * row["meo_usage_ratio"]))
    print("Wrote:", png)
    print("Wrote:", pdf)
    print("Wrote:", csv_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
