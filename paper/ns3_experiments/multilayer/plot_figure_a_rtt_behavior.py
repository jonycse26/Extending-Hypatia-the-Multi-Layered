#!/usr/bin/env python3
"""
Figure A — RTT behavior (3-pair comparison)

Uses run_list experiment-1 pairs:
  - LEO-only pairs from experiment1_pairs_leo
  - Multilayer pairs from experiment1_pairs_multilayer

Creates two figures, each with 3 panels:
  1) LEO-only (three source/destination pairs)
  2) Multilayer (matching three source/destination pairs)

Expects CSVs under data/<run_name>/ from ns-3 runs built with the same simulation
length and dynamic_state update interval as run_list (default: simulation_end_time_s=25,
dynamic_state_update_interval_ms=1000 → dynamic_state_1000ms_for_25s).
"""

import argparse
import csv
import os
import re
import sys
import warnings

import matplotlib
# Figure A is 2D-only; silence irrelevant 3D projection warning from mixed matplotlib installs.
warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-a rtt behavior")
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


def _series_are_identical(x1, y1, x2, y2, eps=1e-9):
    if len(x1) != len(x2) or len(y1) != len(y2):
        return False
    if not x1:
        return False
    for a, b in zip(x1, x2):
        if abs(a - b) > eps:
            return False
    for a, b in zip(y1, y2):
        if abs(a - b) > eps:
            return False
    return True


def _parse_from_to_from_pings_run(run_name):
    m = re.match(r"^.*_(\d+)_to_(\d+)_pings$", run_name)
    if not m:
        raise ValueError("Invalid pings run name: %s" % run_name)
    return int(m.group(1)), int(m.group(2))


def _read_computed_rtt_csv(path):
    xs, ys = [], []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                xs.append(float(row[0]) / 1e9)
                ys.append(float(row[1]))
            except ValueError:
                continue
    return xs, ys


def _read_computed_rtt_series(data_dir):
    """
    Load computed_rtt_ms_ts.csv, or create it from tcp_flow_0_rtt.csv (same as
    evaluation_utils.plot_tcp_flow post-processing) if missing.
    """
    path = os.path.join(data_dir, "computed_rtt_ms_ts.csv")
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        xs, ys = _read_computed_rtt_csv(path)
        return xs, ys, path

    tcp_path = os.path.join(data_dir, "tcp_flow_0_rtt.csv")
    if not os.path.isfile(tcp_path):
        raise FileNotFoundError(
            "Missing %s and %s.\n"
            "  Prereq: constellation dynamic_state matches run_list (e.g. step_0).\n"
            "  Then from multilayer/: create runs, simulate, export CSVs — for one pair, e.g. Lima–Karachi (index 1):\n"
            "    python3 example_2_comparison.py --only-pair-indices 1 --with-pings --run-ns3\n"
            "  Or full pipeline: python3 step_1_generate_runs.py && python3 step_2_run.py && python3 step_3_generate_plots.py\n"
            "  (step_1 clears runs/pdf/data; prefer example_2 line above if you only need missing Figure A dirs.)"
            % (path, tcp_path)
        )
    if os.path.getsize(tcp_path) == 0:
        raise FileNotFoundError("Empty %s; cannot build computed_rtt_ms_ts.csv" % tcp_path)

    xs, ys = [], []
    lines_out = []
    with open(tcp_path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                t_ns = float(row[1])
                rtt_ms = float(row[2]) / 1e6
            except ValueError:
                continue
            xs.append(t_ns / 1e9)
            ys.append(rtt_ms)
            lines_out.append("%.0f,%.10f\n" % (t_ns, rtt_ms))

    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(path, "w") as f_out:
            f_out.writelines(lines_out)
        print("NOTE: Wrote %s (derived from tcp_flow_0_rtt.csv)" % path)
    except OSError as exc:
        print("NOTE: Could not write %s (%s); plotted computed RTT from TCP in memory" % (path, exc))

    if not xs:
        raise RuntimeError("No RTT samples in %s" % tcp_path)
    return xs, ys, path


def _read_tcp_rtt_series(data_dir):
    path = os.path.join(data_dir, "tcp_flow_0_rtt.csv")
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


def _read_ping_rtt_series(data_dir, pings_run_name):
    from_id, to_id = _parse_from_to_from_pings_run(pings_run_name)
    path = os.path.join(data_dir, "ping_%d_to_%d_rtt.csv" % (from_id, to_id))
    xs = []
    ys = []
    with open(path, "r") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            try:
                t_s = float(row[2]) / 1e9
                rtt_ns = float(row[3])
            except ValueError:
                continue
            # In plot_ping, lost packets are written as RTT=0 -> skip from measured RTT line.
            if rtt_ns <= 0:
                continue
            xs.append(t_s)
            ys.append(rtt_ns / 1e6)
    return xs, ys, path


def _assert_exists(path):
    if not os.path.isfile(path):
        raise FileNotFoundError("Missing file: %s" % path)


def _clip_series_to_time_s(xs, ys, t_max_s):
    """Keep samples with time <= t_max_s (simulation window)."""
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


def _expected_fstate_file_count(duration_s, time_step_ms):
    """
    Matches check_progress / forwarding-state grid: one snapshot each time_step_ms
    from t=0 through t=duration_s inclusive.
    """
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _load_panel_series(tcp_run_name, pings_run_name):
    tcp_data_dir = os.path.join(SCRIPT_DIR, "data", tcp_run_name)
    ping_data_dir = os.path.join(SCRIPT_DIR, "data", pings_run_name)

    comp_x, comp_y, comp_path = _read_computed_rtt_series(tcp_data_dir)
    tcp_x, tcp_y, tcp_path = _read_tcp_rtt_series(tcp_data_dir)
    ping_x, ping_y, ping_path = _read_ping_rtt_series(ping_data_dir, pings_run_name)

    _assert_exists(tcp_path)
    _assert_exists(ping_path)

    if not comp_x or not tcp_x or not ping_x:
        raise RuntimeError(
            "One or more RTT inputs are empty for tcp=%s pings=%s"
            % (tcp_run_name, pings_run_name)
        )

    return {
        "computed": (comp_x, comp_y),
        "tcp": (tcp_x, tcp_y),
        "ping": (ping_x, ping_y),
        "paths": {
            "computed": comp_path,
            "tcp": tcp_path,
            "ping": ping_path,
        },
    }


def _plot_three_panels(panels, out_png, out_pdf, time_window_s):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    data_t_max = 0.0
    for i, (title, panel) in enumerate(panels):
        ax = axes[i]
        x_comp, y_comp = panel["computed"]
        x_ping, y_ping = panel["ping"]
        x_tcp, y_tcp = panel["tcp"]
        for xv in (x_comp, x_ping, x_tcp):
            if xv:
                data_t_max = max(data_t_max, max(xv))
        comp_equals_tcp = _series_are_identical(x_comp, y_comp, x_tcp, y_tcp)
        x_comp, y_comp = _clip_series_to_time_s(x_comp, y_comp, time_window_s)
        x_ping, y_ping = _clip_series_to_time_s(x_ping, y_ping, time_window_s)
        x_tcp, y_tcp = _clip_series_to_time_s(x_tcp, y_tcp, time_window_s)

        # Draw TCP first, then ping, then computed on top so computed is always visible.
        ax.plot(x_tcp, y_tcp, lw=1.6, alpha=0.8, color="#2ca02c", label="tcp_rtt_ms_ts", zorder=2)
        ax.plot(x_ping, y_ping, lw=1.6, alpha=0.9, color="#ff7f0e", label="ping_rtt_ms_ts", zorder=3)
        ax.plot(
            x_comp,
            y_comp,
            lw=2.2,
            linestyle="--",
            color="#1f77b4",
            label="computed_rtt_ms_ts",
            zorder=4,
        )
        if comp_equals_tcp:
            print("WARNING: %s panel -> computed_rtt_ms_ts is identical to tcp_rtt_ms_ts (curves overlap)." % title)
            ax.text(
                0.02,
                0.04,
                "computed == tcp (overlap)",
                transform=ax.transAxes,
                fontsize=8,
                color="#1f77b4",
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"),
            )
        ax.set_title(title)
        ax.set_xlabel("Time (s)")
        ax.set_xlim(0.0, float(time_window_s))
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("RTT (ms)")
    axes[2].legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    # Keep full [0, duration_s] window after layout (avoids autoscale quirks).
    for ax in axes:
        ax.set_xlim(0.0, float(time_window_s))

    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING: Latest RTT sample t≈%.3f s < x-axis end %.3f s — CSVs look like a shorter sim; re-run ns-3 for full %d s."
            % (data_t_max, float(time_window_s), int(time_window_s))
        )

    out_dir_png = os.path.dirname(os.path.abspath(out_png))
    out_dir_pdf = os.path.dirname(os.path.abspath(out_pdf))
    os.makedirs(out_dir_png, exist_ok=True)
    os.makedirs(out_dir_pdf, exist_ok=True)

    fig.savefig(out_png, dpi=200)
    fig.savefig(out_pdf)
    plt.close(fig)

    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(description="Plot Figure A RTT behavior (3-pair LEO and Multilayer).")
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Simulation length: x-axis [0, duration_s], clip series, title. Default: run_list.simulation_end_time_s.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Dynamic state update interval in ms (for figure annotation). Default: run_list.dynamic_state_update_interval_ms.",
    )
    parser.add_argument(
        "--leo-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_a_rtt_behavior_leo_only"),
        help="Output prefix for LEO-only figure (without extension).",
    )
    parser.add_argument(
        "--ml-out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_a_rtt_behavior_multilayer"),
        help="Output prefix for Multilayer figure (without extension).",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure A: x-axis [0, %d] s; forwarding-state files ≈ %d (duration_s×1000/time_step_ms + 1)"
        % (args.duration_s, n_fstate)
    )

    try:
        leo_panels = []
        for i, (from_id, to_id, desc) in enumerate(experiment1_pairs_leo):
            run_tcp = "leo_only_%d_to_%d_tcp" % (from_id, to_id)
            run_ping = "leo_only_%d_to_%d_pings" % (from_id, to_id)
            panel = _load_panel_series(run_tcp, run_ping)
            title = "(%s) %s" % (chr(ord("a") + i), desc)
            leo_panels.append((title, panel))

        ml_panels = []
        for i, (from_id, to_id, desc) in enumerate(experiment1_pairs_multilayer):
            run_tcp = "multilayer_%d_to_%d_tcp" % (from_id, to_id)
            run_ping = "multilayer_%d_to_%d_pings" % (from_id, to_id)
            panel = _load_panel_series(run_tcp, run_ping)
            title = "(%s) %s" % (chr(ord("a") + i), desc)
            ml_panels.append((title, panel))
    except Exception as e:
        print("ERROR:", str(e))
        return 1

    _plot_three_panels(
        leo_panels,
        args.leo_out_prefix + ".png",
        args.leo_out_prefix + ".pdf",
        args.duration_s,
    )
    _plot_three_panels(
        ml_panels,
        args.ml_out_prefix + ".png",
        args.ml_out_prefix + ".pdf",
        args.duration_s,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

