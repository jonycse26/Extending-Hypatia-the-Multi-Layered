#!/usr/bin/env python3
"""
Figure M — Unused bandwidth (LEO-only vs Multilayer)

For each experiment-1 pair (three panels), overlay:
  - LEO-only:   unused = max(0, C − throughput) — thick blue
  - Multilayer: unused = max(0, C − throughput) — thin grey

C (Mb/s) is read per run from ``runs/<run_name>/config_ns3.properties``:
``gsl_data_rate_megabit_per_s`` (falls back to ``isl_data_rate_megabit_per_s``, then 10.0).
This matches the nominal satellite access / ISL rate in these experiments (often 10 Mb/s).

Throughput comes from ``data/<run>/tcp_flow_0_rate_in_intervals.csv`` (same as Figure C).

Optional vertical highlight band (e.g. handoff window): ``--highlight-start-s`` /
``--highlight-end-s``.

Align with ``run_list`` timing (default: 25 s sim, 1000 ms state updates).
"""

import argparse
import csv
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-m unused bandwidth")
RUNS_DIR = os.path.join(SCRIPT_DIR, "runs")
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


def _read_throughput_mbps_ts(run_name):
    path = os.path.join(SCRIPT_DIR, "data", run_name, "tcp_flow_0_rate_in_intervals.csv")
    xs, ys = [], []
    if not os.path.isfile(path):
        return xs, ys, path
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


def _read_cap_mbps_from_config(run_name):
    """
    Return nominal link capacity Mb/s from runs/<run>/config_ns3.properties.
    """
    path = os.path.join(RUNS_DIR, run_name, "config_ns3.properties")
    default = 10.0
    if not os.path.isfile(path):
        print("WARNING: missing %s; using cap=%.1f Mb/s" % (path, default))
        return default, path
    cap = None
    gsl = None
    isl = None
    with open(path, "r") as f:
        for line in f:
            line = line.split("#")[0].strip()
            m = re.match(r"^gsl_data_rate_megabit_per_s\s*=\s*([0-9.+-eE]+)\s*$", line)
            if m:
                gsl = float(m.group(1))
            m = re.match(r"^isl_data_rate_megabit_per_s\s*=\s*([0-9.+-eE]+)\s*$", line)
            if m:
                isl = float(m.group(1))
    if gsl is not None:
        cap = gsl
    elif isl is not None:
        cap = isl
    else:
        cap = default
        print("WARNING: no gsl/isl rate in %s; using cap=%.1f Mb/s" % (path, default))
    return cap, path


def _unused_mbps_series(tx, ty_mbps, cap_mbps):
    if not tx:
        return [], []
    unused = [max(0.0, float(cap_mbps) - float(y)) for y in ty_mbps]
    return tx, unused


def _plot_figure_m(
    panels,
    out_prefix,
    time_window_s,
    time_step_ms,
    highlight_start_s,
    highlight_end_s,
    ylim_max,
):
    """
    panels: list of (panel_title, t_leo, u_leo, t_ml, u_ml, cap_leo, cap_ml)
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.0), sharey=True)
    data_t_max = 0.0
    global_ymax = 0.0

    for i, (panel_title, t_leo, u_leo, t_ml, u_ml, cap_leo, cap_ml) in enumerate(panels):
        ax = axes[i]
        for xv in (t_leo, t_ml):
            if xv:
                data_t_max = max(data_t_max, max(xv))
        for yv in (u_leo, u_ml):
            if yv:
                global_ymax = max(global_ymax, max(yv))
        global_ymax = max(global_ymax, cap_leo, cap_ml)

        if (
            highlight_start_s is not None
            and highlight_end_s is not None
            and highlight_end_s > highlight_start_s
        ):
            ax.axvspan(
                highlight_start_s,
                highlight_end_s,
                facecolor="#ffcccc",
                edgecolor="none",
                alpha=0.55,
                zorder=0,
            )

        ax.plot(
            t_leo,
            u_leo,
            color="#1f77b4",
            lw=2.6,
            solid_capstyle="round",
            label="LEO-only",
            zorder=3,
        )
        ax.plot(
            t_ml,
            u_ml,
            color="#9e9e9e",
            lw=1.15,
            solid_capstyle="round",
            label="Multilayer",
            zorder=2,
        )

        ax.set_title(panel_title, fontsize=11)
        ax.set_xlabel("Time (s)")
        ax.grid(True, linestyle=":", alpha=0.65)
        ax.set_xlim(0.0, float(time_window_s))

    ymax = float(ylim_max) if ylim_max is not None and ylim_max > 0 else global_ymax * 1.08
    ymax = max(ymax, 1.0)
    for ax in axes:
        ax.set_ylim(0.0, ymax)

    axes[0].set_ylabel("Unused bandwidth (Mb/s)", fontsize=11)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=9, frameon=True, bbox_to_anchor=(0.5, 1.02))

    fig.suptitle(
        "Figure M — Unused bandwidth (nominal GSL/ISL rate − measured TCP throughput)"
        + " — %d s sim, %d ms state updates" % (time_window_s, time_step_ms),
        fontsize=11,
        y=1.12,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.88])

    if data_t_max + 0.05 < float(time_window_s):
        print(
            "WARNING (%s): latest sample t≈%.3f s < x-axis end %.0f s."
            % (os.path.basename(out_prefix), data_t_max, float(time_window_s))
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
    parser = argparse.ArgumentParser(description="Plot Figure M (unused bandwidth LEO vs multilayer).")
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Clip series and x-axis [0, duration_s]. Default: run_list.simulation_end_time_s.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Annotation only. Default: run_list.dynamic_state_update_interval_ms.",
    )
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_m_unused_bandwidth"),
        help="Output path prefix (adds .png / .pdf).",
    )
    parser.add_argument(
        "--highlight-start-s",
        type=float,
        default=None,
        help="Optional start of shaded vertical band (seconds).",
    )
    parser.add_argument(
        "--highlight-end-s",
        type=float,
        default=None,
        help="Optional end of shaded vertical band (seconds).",
    )
    parser.add_argument(
        "--ylim-max",
        type=float,
        default=None,
        help="Force y-axis max (Mb/s); default auto from data and nominal caps.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure M: x-axis [0, %d] s; forwarding-state files ≈ %d"
        % (args.duration_s, n_fstate)
    )

    panels = []
    try:
        for i, ((f_leo, t_leo, desc), (f_ml, t_ml, _)) in enumerate(
            zip(experiment1_pairs_leo, experiment1_pairs_multilayer)
        ):
            run_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
            run_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
            cap_leo, _ = _read_cap_mbps_from_config(run_leo)
            cap_ml, _ = _read_cap_mbps_from_config(run_ml)
            tx_l, ty_l, path_l = _read_throughput_mbps_ts(run_leo)
            tx_m, ty_m, path_m = _read_throughput_mbps_ts(run_ml)
            if not tx_l or not tx_m:
                raise RuntimeError(
                    "Missing/empty throughput for pair %s: leo=%s ml=%s" % (desc, path_l, path_m)
                )
            tx_l, ty_l = _clip_series_to_time_s(tx_l, ty_l, args.duration_s)
            tx_m, ty_m = _clip_series_to_time_s(tx_m, ty_m, args.duration_s)
            uxl, uyl = _unused_mbps_series(tx_l, ty_l, cap_leo)
            uxm, uym = _unused_mbps_series(tx_m, ty_m, cap_ml)
            panel_title = "(%s) %s" % (chr(ord("a") + i), desc)
            panels.append((panel_title, uxl, uyl, uxm, uym, cap_leo, cap_ml))
            print(
                "  %s: cap_leo=%.3f cap_ml=%.3f Mb/s"
                % (panel_title, cap_leo, cap_ml)
            )
    except Exception as e:
        print("ERROR:", str(e))
        return 1

    _plot_figure_m(
        panels,
        args.out_prefix,
        args.duration_s,
        args.time_step_ms,
        args.highlight_start_s,
        args.highlight_end_s,
        args.ylim_max,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
