#!/usr/bin/env python3
"""
Figure C — Protocol outcome over time

Objective:
  Show combined transport behavior over time.

Inputs:
  - tcp_rtt_ms_ts      : data/<run>/tcp_flow_0_rtt.csv
  - throughput_mbps_ts : data/<run>/tcp_flow_0_rate_in_intervals.csv

Layout:
  - Three-panel figures: LEO-only and Multilayer (experiment-1 pairs a–c).
  - Combined figure: two columns (LEO-only | Multilayer) for one pair (default: long-haul,
    Tokyo–Buenos-Aires, pair index 2).

Align with ``run_list`` timing (default: 25 s sim, 1000 ms state updates →
``dynamic_state_1000ms_for_25s``).
"""

import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-c protocol outcome")
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


def _clip_panel(panel, t_max_s):
    rx, ry = panel["rtt"]
    tx, ty = panel["thr"]
    return {
        "rtt": _clip_series_to_time_s(rx, ry, t_max_s),
        "thr": _clip_series_to_time_s(tx, ty, t_max_s),
    }


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _read_tcp_rtt_ms_ts(run_name):
    path = os.path.join(SCRIPT_DIR, "data", run_name, "tcp_flow_0_rtt.csv")
    xs = []
    ys = []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                xs.append(float(row[1]) / 1e9)
                ys.append(float(row[2]) / 1e6)
            except ValueError:
                continue
    return xs, ys, path


def _read_throughput_mbps_ts(run_name):
    path = os.path.join(SCRIPT_DIR, "data", run_name, "tcp_flow_0_rate_in_intervals.csv")
    xs = []
    ys = []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                xs.append(float(row[1]) / 1e9)
                ys.append(float(row[2]))
            except ValueError:
                continue
    return xs, ys, path


def _load_panel(run_name):
    rtt_x, rtt_y, rtt_path = _read_tcp_rtt_ms_ts(run_name)
    thr_x, thr_y, thr_path = _read_throughput_mbps_ts(run_name)

    if not rtt_x or not thr_x:
        raise RuntimeError(
            "Missing/empty time series for %s (rtt=%s, thr=%s)"
            % (run_name, rtt_path, thr_path)
        )

    return {
        "rtt": (rtt_x, rtt_y),
        "thr": (thr_x, thr_y),
    }


def _plot_one_panel(ax, panel_title, panel_data):
    rtt_x, rtt_y = panel_data["rtt"]
    thr_x, thr_y = panel_data["thr"]

    # Left y-axis: RTT
    l1 = ax.plot(rtt_x, rtt_y, color="#1f77b4", lw=1.8, label="tcp_rtt_ms_ts")
    ax.set_ylabel("RTT (ms)", color="#1f77b4")
    ax.tick_params(axis="y", labelcolor="#1f77b4")
    ax.set_xlabel("Time (s)")
    ax.grid(True, alpha=0.3)
    ax.set_title(panel_title)

    # Right y-axis: Throughput
    ax2 = ax.twinx()
    l2 = ax2.plot(thr_x, thr_y, color="#ff7f0e", lw=1.8, linestyle="--", label="throughput_mbps_ts")
    ax2.set_ylabel("Throughput (Mbps)", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")

    return l1 + l2


def _plot_three_panels(panels, fig_title, out_prefix, time_window_s):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    legend_handles = None
    legend_labels = None
    data_t_max = 0.0
    for i, (panel_title, panel_data) in enumerate(panels):
        for key in ("rtt", "thr"):
            xv = panel_data[key][0]
            if xv:
                data_t_max = max(data_t_max, max(xv))
        handles = _plot_one_panel(axes[i], panel_title, panel_data)
        axes[i].set_xlim(0.0, float(time_window_s))
        if legend_handles is None:
            legend_handles = handles
            legend_labels = [h.get_label() for h in handles]

    # Keep legend only in the last panel to avoid clutter.
    axes[2].legend(legend_handles, legend_labels, loc="upper left", fontsize=8)
    fig.tight_layout()
    for ax in axes:
        ax.set_xlim(0.0, float(time_window_s))

    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (%s): latest sample t≈%.3f s < x-axis end %.0f s."
            % (os.path.basename(out_prefix), data_t_max, float(time_window_s))
        )

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=200)
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def _plot_two_panel_leo_vs_ml(leo_panel, ml_panel, pair_description, fig_title, out_prefix, time_window_s):
    """One row, two columns: LEO-only vs Multilayer for the same city pair."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    data_t_max = 0.0
    for panel_data in (leo_panel, ml_panel):
        for key in ("rtt", "thr"):
            xv = panel_data[key][0]
            if xv:
                data_t_max = max(data_t_max, max(xv))

    h0 = _plot_one_panel(axes[0], "LEO-only", leo_panel)
    axes[0].set_xlim(0.0, float(time_window_s))
    _plot_one_panel(axes[1], "Multilayer", ml_panel)
    axes[1].set_xlim(0.0, float(time_window_s))

    labels = [h.get_label() for h in h0]
    axes[0].legend(h0, labels, loc="upper left", fontsize=8)

    fig.tight_layout()
    for ax in axes:
        ax.set_xlim(0.0, float(time_window_s))

    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (%s): latest sample t≈%.3f s < x-axis end %.0f s."
            % (os.path.basename(out_prefix), data_t_max, float(time_window_s))
        )

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=200)
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(
        description="Plot Figure C (protocol outcome over time) for experiment-1 three pairs."
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Clip series and set x-axis [0, duration_s]. Default: run_list.simulation_end_time_s.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Annotation + fstate count print. Default: run_list.dynamic_state_update_interval_ms.",
    )
    parser.add_argument(
        "--leo-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_c_protocol_outcome_leo_only"),
        help="Output prefix for LEO-only 3-panel figure.",
    )
    parser.add_argument(
        "--ml-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_c_protocol_outcome_multilayer"),
        help="Output prefix for Multilayer 3-panel figure.",
    )
    parser.add_argument(
        "--combined-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_c_protocol_outcome"),
        help="Output prefix for 2-panel LEO vs Multilayer comparison figure.",
    )
    parser.add_argument(
        "--combined-pair-index",
        type=int,
        default=2,
        help="0-based experiment-1 pair for the 2-panel figure (default: 2 = Tokyo–Buenos-Aires).",
    )
    parser.add_argument(
        "--no-combined",
        action="store_true",
        help="Skip the 2-panel LEO vs Multilayer figure.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure C: x-axis [0, %d] s; forwarding-state files ≈ %d (duration_s×1000/time_step_ms + 1)"
        % (args.duration_s, n_fstate)
    )
    if args.combined_pair_index < 0 or args.combined_pair_index >= len(experiment1_pairs_leo):
        print(
            "ERROR: --combined-pair-index must be in [0, %d)"
            % len(experiment1_pairs_leo)
        )
        return 1

    try:
        leo_panels = []
        leo_panels_raw = []
        for i, (from_id, to_id, desc) in enumerate(experiment1_pairs_leo):
            run_name = "leo_only_%d_to_%d_tcp" % (from_id, to_id)
            panel = _clip_panel(_load_panel(run_name), args.duration_s)
            leo_panels.append(("(%s) %s" % (chr(ord("a") + i), desc), panel))
            leo_panels_raw.append(panel)

        ml_panels = []
        ml_panels_raw = []
        for i, (from_id, to_id, desc) in enumerate(experiment1_pairs_multilayer):
            run_name = "multilayer_%d_to_%d_tcp" % (from_id, to_id)
            panel = _clip_panel(_load_panel(run_name), args.duration_s)
            ml_panels.append(("(%s) %s" % (chr(ord("a") + i), desc), panel))
            ml_panels_raw.append(panel)
    except Exception as e:
        print("ERROR:", str(e))
        return 1

    _plot_three_panels(
        leo_panels,
        "Figure C — Protocol outcome over time (LEO-only)",
        args.leo_out_prefix,
        args.duration_s,
    )
    _plot_three_panels(
        ml_panels,
        "Figure C — Protocol outcome over time (Multilayer)",
        args.ml_out_prefix,
        args.duration_s,
    )

    if not args.no_combined:
        j = args.combined_pair_index
        _pair_desc = experiment1_pairs_leo[j][2]
        _plot_two_panel_leo_vs_ml(
            leo_panels_raw[j],
            ml_panels_raw[j],
            _pair_desc,
            "Figure C — Protocol outcome over time",
            args.combined_out_prefix,
            args.duration_s,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

