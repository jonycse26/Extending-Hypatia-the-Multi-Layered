#!/usr/bin/env python3
"""
Figure V — Experiment 3 (multilayer): (a) distance vs. MEO scatter + (b) hop count vs. MEO usage

**Left (a):** distance (km) vs. ``meo_usage_ratio`` (0–100%%), tier labels, dashed tier-order line.

**Right (b):** satellite hop count vs. MEO usage (pooled multilayer fstate snapshots); same plot as
``plot_figure_v_meo_usage_by_hop.py``.

Defaults match ``run_list`` (``duration_s=25``, ``time_step_ms=1000`` →
``dynamic_state_1000ms_for_25s``). Override with CLI flags.

Output: ``figure-v example3 multilayer meo/figure_v_example3_multilayer_meo_bars.{png,pdf}``.
"""

import argparse
import os
import sys
import warnings

import matplotlib

warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-v example3 multilayer meo")
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
from evaluation_utils import aggregate_meo_usage_by_hop, extract_metrics
from plot_figure_v_meo_usage_by_hop import (
    DEFAULT_HOP_BINS,
    _all_multilayer_tcp_run_names,
    _example3_multilayer_run_names,
    _plot_meo_hop_scatter,
    _pool_hop_meo_snapshots,
    _series_from_bins,
)

DEFAULT_SCENARIO_CSV = os.path.join(SCRIPT_DIR, "example_3_distance_scenario_results.csv")
DEFAULT_METRICS_CSV = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")

MEO_PCT_PAD = 10.0


def _to_float(v):
    try:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return float("nan")
        return float(v)
    except Exception:
        return float("nan")


def _meo_from_run(run_name, metrics_duration_s, metrics_time_step_ms):
    """``meo_usage_ratio`` from ``fstate`` for the requested duration / time step."""
    for rd in figu._run_dir_candidates(run_name):
        if not os.path.isdir(rd):
            continue
        met = extract_metrics(
            rd,
            metrics_duration_s=metrics_duration_s,
            metrics_time_step_ms=metrics_time_step_ms,
        )
        if met.get("error"):
            continue
        v = _to_float(met.get("meo_usage_ratio"))
        if v == v:
            return v
    return float("nan")


def _meo_for_tier(
    scenario_row,
    metrics_by_run,
    run_name_fallback=None,
    metrics_duration_s=None,
    metrics_time_step_ms=None,
):
    rn = (run_name_fallback or "").strip()
    if not rn and scenario_row:
        rn = (scenario_row.get("run_name") or "").strip()
    if rn and metrics_duration_s is not None and metrics_time_step_ms is not None:
        v = _meo_from_run(rn, metrics_duration_s, metrics_time_step_ms)
        if v == v:
            return v
    if scenario_row:
        v = _to_float(scenario_row.get("meo_usage_ratio"))
        if v == v:
            return v
        if rn and rn in metrics_by_run:
            v = _to_float(metrics_by_run[rn].get("meo_usage_ratio"))
            if v == v:
                return v
    if rn and rn in metrics_by_run:
        v = _to_float(metrics_by_run[rn].get("meo_usage_ratio"))
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


def _meo_scatter_series(
    scenario_by_tier, metrics_by_run, tier_km, metrics_duration_s, metrics_time_step_ms
):
    tier_run = figu._tier_run_names_multilayer(scenario_by_tier)
    if len(tier_run) != len(tier_km):
        raise ValueError(
            "got %d tier runs but %d km values (check scenario / run_list vs --tier-km)."
            % (len(tier_run), len(tier_km))
        )
    xs, ys, labels = [], [], []
    for (tier, rn), km in zip(tier_run, tier_km):
        row = scenario_by_tier.get(tier)
        y = _meo_for_tier(
            row,
            metrics_by_run,
            run_name_fallback=rn,
            metrics_duration_s=metrics_duration_s,
            metrics_time_step_ms=metrics_time_step_ms,
        )
        if y != y:
            continue
        xs.append(km)
        ys.append(y)
        if row and row.get("pair"):
            labels.append(_short_pair_label(row.get("pair")))
        else:
            labels.append(tier.capitalize())
    return xs, ys, labels


def _plot_meo_distance_scatter(ax, xs, ys, labels, no_trend):
    if not xs:
        ax.text(0.5, 0.5, "no MEO data", ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_title("(a) Distance vs. MEO usage", fontsize=11)
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
            label="Tier order",
        )
    xmax = max(xs)
    for km, y, lab in zip(xs, ys_pct, labels):
        text = (lab or "").strip() or "%.0f km" % km
        near_right = xmax > 0 and km >= 0.92 * xmax
        if y <= 0.0:
            ax.annotate(
                text,
                (km, y),
                textcoords="offset points",
                xytext=(0, 8),
                fontsize=7.5,
                color="#222222",
                ha="center",
                va="bottom",
            )
        elif near_right:
            # Label below the top marker so "Long" stays inside the axes.
            ax.annotate(
                text,
                (km, y),
                textcoords="offset points",
                xytext=(0, -10),
                fontsize=7.5,
                color="#222222",
                ha="center",
                va="top",
            )
        else:
            ax.annotate(
                text,
                (km, y),
                textcoords="offset points",
                xytext=(6, 8),
                fontsize=7.5,
                color="#222222",
                ha="left",
                va="bottom",
            )
    ax.set_xlabel("Representative distance (km)", fontsize=9)
    ax.set_ylabel("MEO usage (%)", fontsize=9)
    ax.set_title("(a) Distance vs. MEO usage", fontsize=11)
    y_lo = -MEO_PCT_PAD
    y_hi = 100.0 + MEO_PCT_PAD
    ax.set_ylim(y_lo, y_hi)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xlim(0.0, max(xmax * 1.06, 500.0) if xmax > 0 else 1.0)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8, color="#888888", alpha=0.55, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=7, framealpha=0.92)
    # Solid frame on all four sides; 0%%/100%% stay on dotted grid only.
    frame_kw = dict(linewidth=1.0, color="#333333")
    for side in ("left", "right", "bottom", "top"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_zorder(10)
        for key, val in frame_kw.items():
            setattr(ax.spines[side], key, val)


def _parse_hop_bins(s):
    try:
        return tuple(int(x.strip()) for x in s.split(",") if x.strip())
    except ValueError:
        raise ValueError("invalid --hop-bins %r" % s)


def main():
    p = argparse.ArgumentParser(
        description="Figure V: (a) distance vs MEO scatter, (b) hop count vs MEO usage (experiment 3)."
    )
    p.add_argument("--scenario-csv", default=DEFAULT_SCENARIO_CSV, help="example_3_distance_scenario_results.csv")
    p.add_argument(
        "--metrics-csv",
        default=DEFAULT_METRICS_CSV,
        help="multilayer_all_experiments_metrics.csv",
    )
    p.add_argument(
        "--tier-km",
        default="2800,4500,11000",
        help="Comma-separated km for short,medium,long (Figure W defaults).",
    )
    p.add_argument(
        "--no-trend",
        action="store_true",
        help="Do not draw tier-order (a) or hop-order (b) dashed lines.",
    )
    p.add_argument(
        "--example3-only",
        action="store_true",
        help="Panel (b): only the three example-3 multilayer TCP runs.",
    )
    p.add_argument(
        "--hop-bins",
        default=",".join(str(h) for h in DEFAULT_HOP_BINS),
        help="Panel (b): comma-separated satellite hop counts (default: 2,3,4,5).",
    )
    p.add_argument("--out-prefix", default=None, help="Output path without extension.")
    p.add_argument(
        "--duration-s",
        type=float,
        default=float(simulation_end_time_s),
        help="fstate window for both panels (default: run_list).",
    )
    p.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Forwarding-state step for both panels (default: run_list).",
    )
    args = p.parse_args()

    try:
        tier_km = _parse_tier_km(args.tier_km)
    except ValueError as e:
        print("ERROR:", e)
        return 1

    try:
        hop_bins = _parse_hop_bins(args.hop_bins)
    except ValueError as e:
        print("ERROR:", e)
        return 1

    out_prefix = args.out_prefix or os.path.join(FIGURE_DIR, "figure_v_example3_multilayer_meo_bars")

    scenario_by_tier = figu._load_scenario_by_tier(args.scenario_csv)
    metrics_by_run = figu._load_metrics_rows(args.metrics_csv)
    dur = float(args.duration_s)
    step_ms = int(args.time_step_ms)

    try:
        sx, sy, slabels = _meo_scatter_series(
            scenario_by_tier, metrics_by_run, tier_km, dur, step_ms
        )
    except ValueError as e:
        print("ERROR:", e)
        return 1

    if not sx:
        print("ERROR: no meo_usage_ratio values (check %s and %s)" % (args.scenario_csv, args.metrics_csv))
        return 1

    if args.example3_only:
        hop_run_names = _example3_multilayer_run_names(args.scenario_csv)
    else:
        hop_run_names = _all_multilayer_tcp_run_names()

    hop_snapshots, hop_used_runs = _pool_hop_meo_snapshots(hop_run_names, dur, step_ms)
    if not hop_snapshots:
        print(
            "ERROR: no fstate snapshots for panel (b) "
            "(check runs/ and dynamic_state_%dms_for_%.0fs)" % (step_ms, dur)
        )
        return 1

    hop_agg = aggregate_meo_usage_by_hop(hop_snapshots, hop_bins=hop_bins)
    hx, hy, hlabels, hns = _series_from_bins(hop_bins, hop_agg)
    if not hx:
        print(
            "ERROR: no samples in hop bins %s for panel (b) (total snapshots: %d)"
            % (hop_bins, len(hop_snapshots))
        )
        return 1

    fig = plt.figure(figsize=(11.0, 3.15), layout="constrained")
    outer = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[1.0, 1.0], wspace=0.28)
    ax_meo = fig.add_subplot(outer[0, 0])
    ax_hop = fig.add_subplot(outer[0, 1])

    _plot_meo_distance_scatter(ax_meo, sx, sy, slabels, args.no_trend)
    _plot_meo_hop_scatter(
        ax_hop,
        hx,
        hy,
        hlabels,
        hns,
        hop_bins,
        args.no_trend,
        title="(b) Hop count vs. MEO usage",
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    png = out_prefix + ".png"
    pdf = out_prefix + ".pdf"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)

    print(
        "Figure V: dynamic_state_%dms_for_%.0fs · (b) %d runs · %d hop snapshots"
        % (step_ms, dur, len(hop_used_runs), len(hop_snapshots))
    )
    for hop in hop_bins:
        row = hop_agg.get(hop)
        if row:
            print("  hop %d: n=%d  meo_usage=%.1f%%" % (hop, row["n"], 100.0 * row["meo_usage_ratio"]))
    print("Wrote:", png)
    print("Wrote:", pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
