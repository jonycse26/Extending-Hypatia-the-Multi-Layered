#!/usr/bin/env python3
"""
Figure K — Cumulative bytes vs time (LEO-only vs Multilayer)

Objective:
  Show transferred volume over time from ``tcp_flow_0_progress.csv`` under ``data/<run>/``.
  On long paths, multilayer should appear as a steeper curve and/or reach the same
  cumulative bytes earlier than LEO-only.

Pairs:
  Default: experiment-1 pair index 2 (Tokyo–Buenos-Aires). Use ``--all-pairs`` for
  three panels (short / medium / long). Align time window with ``run_list`` defaults
  (25 s sim, 1000 ms state updates → clip to ``t ≤ duration_s``, ``xlim(0 duration_s)``).
"""

import argparse
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-k cumulative bytes")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list defaults / experiment1 pairs: %s" % e)


def _clip_series_to_time_s(xs, ys, t_max_s):
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _read_progress_bytes_tcp_run(run_tcp_name):
    """time (s), cumulative bytes from tcp_flow_0_progress.csv."""
    path = os.path.join(DATA_DIR, run_tcp_name, "tcp_flow_0_progress.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError("Missing %s" % path)
    xs, ys = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                xs.append(float(row[1]) / 1e9)
                ys.append(float(row[2]))
            except ValueError:
                continue
    if not xs:
        raise RuntimeError("No data points in %s" % path)
    return xs, ys, path


def _bytes_to_mb(b):
    return float(b) / 1.0e6


def _plot_overlay_single(
    leo_tx,
    leo_by,
    ml_tx,
    ml_by,
    pair_desc,
    out_prefix,
    time_window_s,
    title_suffix,
):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    leo_mb = [_bytes_to_mb(b) for b in leo_by]
    ml_mb = [_bytes_to_mb(b) for b in ml_by]
    ax.plot(leo_tx, leo_mb, color="#1f77b4", lw=2.2, ls="--", label="LEO-only")
    ax.plot(ml_tx, ml_mb, color="#2ca02c", lw=2.2, ls="-", label="Multilayer")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Cumulative transferred (MB)")
    ax.set_xlim(0.0, float(time_window_s))
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower right", framealpha=0.92)

    leo_f = leo_mb[-1] if leo_mb else 0.0
    ml_f = ml_mb[-1] if ml_mb else 0.0
    ax.set_title(
        "Figure K — Cumulative bytes vs time%s\n%s" % (title_suffix, pair_desc),
        fontsize=12,
    )
    ax.text(
        0.02,
        0.98,
        "End of window: LEO %.2f MB — Multilayer %.2f MB"
        % (leo_f, ml_f),
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="0.75", alpha=0.9),
    )

    data_t_max = 0.0
    for xv in (leo_tx, ml_tx):
        if xv:
            data_t_max = max(data_t_max, max(xv))
    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (Figure K): latest sample t≈%.3f s < x-axis end %.0f s."
            % (data_t_max, float(time_window_s))
        )

    fig.tight_layout()
    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def _plot_all_pairs(panels, out_prefix, time_window_s, title_suffix):
    """panels: list of (panel_title, leo_tx, leo_by, ml_tx, ml_by)"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.0), sharey=False)
    data_t_max = 0.0
    for ax, (panel_title, leo_tx, leo_by, ml_tx, ml_by) in zip(axes, panels):
        leo_mb = [_bytes_to_mb(b) for b in leo_by]
        ml_mb = [_bytes_to_mb(b) for b in ml_by]
        ax.plot(leo_tx, leo_mb, color="#1f77b4", lw=2.0, ls="--", label="LEO-only")
        ax.plot(ml_tx, ml_mb, color="#2ca02c", lw=2.0, ls="-", label="Multilayer")
        ax.set_title(panel_title, fontsize=10)
        ax.set_xlabel("Time (s)")
        ax.set_xlim(0.0, float(time_window_s))
        ax.grid(True, linestyle=":", alpha=0.6)
        for xv in (leo_tx, ml_tx):
            if xv:
                data_t_max = max(data_t_max, max(xv))
    axes[0].set_ylabel("Cumulative transferred (MB)")
    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Figure K — Cumulative bytes vs time (all experiment-1 pairs)" + title_suffix, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (Figure K all-pairs): latest sample t≈%.3f s < x-axis end %.0f s."
            % (data_t_max, float(time_window_s))
        )
    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(description="Plot Figure K — cumulative bytes vs time (LEO vs Multilayer).")
    parser.add_argument(
        "--pair-index",
        type=int,
        default=2,
        help="Experiment-1 pair index for single overlay (default: 2 = Tokyo–Buenos-Aires).",
    )
    parser.add_argument(
        "--all-pairs",
        action="store_true",
        help="Also write a 3-panel figure for all experiment-1 pairs.",
    )
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(OUT_DIR, "figure_k_cumulative_bytes"),
        help="Output prefix for the default single-pair overlay (no extension).",
    )
    parser.add_argument(
        "--all-pairs-out-prefix",
        default=os.path.join(OUT_DIR, "figure_k_cumulative_bytes_all_pairs"),
        help="Output prefix for --all-pairs figure.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Clip progress series and set x-axis [0, duration_s]. Default: run_list.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Figure caption / fstate count. Default: run_list.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure K: x-axis [0, %d] s; forwarding-state files ≈ %d (duration_s×1000/time_step_ms + 1)"
        % (args.duration_s, n_fstate)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)

    if args.pair_index < 0 or args.pair_index >= len(experiment1_pairs_leo):
        print("ERROR: --pair-index must be in [0, %d)." % len(experiment1_pairs_leo))
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)

    j = args.pair_index
    f_leo, t_leo, desc_leo = experiment1_pairs_leo[j]
    f_ml, t_ml, desc_ml = experiment1_pairs_multilayer[j]
    pair_desc = desc_leo
    if desc_ml != desc_leo:
        pair_desc = "%s (%s)" % (desc_leo, desc_ml)

    leo_run = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
    ml_run = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)

    try:
        leo_tx, leo_by, _ = _read_progress_bytes_tcp_run(leo_run)
        ml_tx, ml_by, _ = _read_progress_bytes_tcp_run(ml_run)
    except (FileNotFoundError, RuntimeError) as e:
        print("ERROR:", e)
        return 1

    leo_tx, leo_by = _clip_series_to_time_s(leo_tx, leo_by, args.duration_s)
    ml_tx, ml_by = _clip_series_to_time_s(ml_tx, ml_by, args.duration_s)

    _plot_overlay_single(
        leo_tx,
        leo_by,
        ml_tx,
        ml_by,
        pair_desc,
        args.out_prefix,
        args.duration_s,
        title_suffix,
    )

    if args.all_pairs:
        panel_list = []
        for i, ((fl, tl, dleo), (fm, tm, dml)) in enumerate(
            zip(experiment1_pairs_leo, experiment1_pairs_multilayer)
        ):
            lr = "leo_only_%d_to_%d_tcp" % (fl, tl)
            mr = "multilayer_%d_to_%d_tcp" % (fm, tm)
            try:
                lx, ly, _ = _read_progress_bytes_tcp_run(lr)
                mx, my, _ = _read_progress_bytes_tcp_run(mr)
            except (FileNotFoundError, RuntimeError) as e:
                print("ERROR (all-pairs panel %d): %s" % (i, e))
                return 1
            lx, ly = _clip_series_to_time_s(lx, ly, args.duration_s)
            mx, my = _clip_series_to_time_s(mx, my, args.duration_s)
            title = "(%s) %s" % (chr(ord("a") + i), dleo)
            panel_list.append((title, lx, ly, mx, my))
        _plot_all_pairs(panel_list, args.all_pairs_out_prefix, args.duration_s, title_suffix)

    return 0


if __name__ == "__main__":
    sys.exit(main())
