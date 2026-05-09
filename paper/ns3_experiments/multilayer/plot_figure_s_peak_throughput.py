#!/usr/bin/env python3
"""
Figure S — Peak TCP throughput: LEO-only vs multilayer (experiment 1 pairs)

For each of the three ``run_list.experiment1`` flows, reads
``data/<run>/tcp_flow_0_rate_in_intervals.csv`` (same as Figures C and M) and reports the
**maximum** interval throughput (Mb/s) over ``[0, duration_s]``.

Also plots the nominal link rate from ``runs/<run>/config_ns3.properties``
(``gsl_data_rate_megabit_per_s`` with the same fallbacks as Figure M) as a dashed reference.

Peaks are taken **raw** from interval rates; a single interval can sit slightly above the
nominal cap because of TCP pacing / windowing and how the rate CSV is derived (same source
as Figure M).

Outputs ``<out-prefix>.png``, ``<out-prefix>.pdf``, and ``<out-prefix>_peaks.csv``.
"""

import argparse
import csv
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-s peak throughput")
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
    raise RuntimeError("Could not import run_list: %s" % e)


def _clip_series_to_time_s(xs, ys, t_max_s):
    if t_max_s is None or t_max_s <= 0:
        return xs, ys
    out_x, out_y = [], []
    for x, y in zip(xs, ys):
        if x <= t_max_s:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y


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
    path = os.path.join(RUNS_DIR, run_name, "config_ns3.properties")
    default = 10.0
    if not os.path.isfile(path):
        print("WARNING: missing %s; using cap=%.1f Mb/s" % (path, default))
        return default, path
    gsl = isl = None
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


def _short_route_label(desc):
    if " to " in desc:
        a, b = desc.split(" to ", 1)
        return "%s→%s" % (a.strip()[:12], b.strip()[:10])
    return desc[:22]


def _plot_bars(rows, out_prefix, duration_s, time_step_ms, ylim_max):
    """
    rows: list of dict with keys desc, short, peak_leo, peak_ml, cap_leo, cap_ml
    """
    n = len(rows)
    x = np.arange(n, dtype=float)
    w = 0.36
    peaks_leo = [r["peak_leo"] for r in rows]
    peaks_ml = [r["peak_ml"] for r in rows]
    caps_leo = [r["cap_leo"] for r in rows]
    caps_ml = [r["cap_ml"] for r in rows]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.bar(x - w / 2, peaks_leo, w, label="LEO-only (peak)", color="#1f77b4", edgecolor="#0d47a1", linewidth=0.6)
    ax.bar(x + w / 2, peaks_ml, w, label="Multilayer (peak)", color="#9e9e9e", edgecolor="#424242", linewidth=0.6)

    cap_ref = max(max(caps_leo), max(caps_ml))
    if len(set(caps_leo + caps_ml)) == 1:
        ax.axhline(
            cap_ref,
            color="#333333",
            linestyle="--",
            linewidth=1.1,
            alpha=0.75,
            label="Nominal link rate (config)",
        )
    else:
        for i in range(n):
            ax.plot([i - w, i], [caps_leo[i], caps_leo[i]], color="#1f77b4", linestyle=":", linewidth=1.0, alpha=0.8)
            ax.plot([i, i + w], [caps_ml[i], caps_ml[i]], color="#616161", linestyle=":", linewidth=1.0, alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels([r["desc"] for r in rows], fontsize=8.5, rotation=18, ha="right")
    ax.set_ylabel("Peak interval throughput (Mb/s)", fontsize=11)
    ax.set_xlabel("Experiment 1 TCP flow", fontsize=10)
    ax.grid(True, axis="y", linestyle=":", alpha=0.65)
    ymax = float(ylim_max) if ylim_max is not None and ylim_max > 0 else max(max(peaks_leo + peaks_ml + [0.1]), cap_ref) * 1.12
    ax.set_ylim(0.0, ymax)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    fig.suptitle(
        "Figure S — Peak TCP throughput (LEO-only vs multilayer)\n"
        "max over tcp_flow_0_rate_in_intervals.csv in [0, %d] s · state update %d ms"
        % (duration_s, time_step_ms),
        fontsize=11,
        y=1.02,
    )
    fig.tight_layout()

    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    p = argparse.ArgumentParser(description="Figure S: peak throughput LEO-only vs multilayer (exp. 1).")
    p.add_argument("--duration-s", type=int, default=simulation_end_time_s, help="Clip throughput series (s).")
    p.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Caption only; default from run_list.",
    )
    p.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_s_peak_throughput"),
        help="Output prefix (.png / .pdf / _peaks.csv).",
    )
    p.add_argument("--ylim-max", type=float, default=None, help="Optional fixed y-axis max (Mb/s).")
    args = p.parse_args()

    rows = []
    try:
        for (f_leo, t_leo, desc), (f_ml, t_ml, _) in zip(
            experiment1_pairs_leo,
            experiment1_pairs_multilayer,
        ):
            run_leo = "leo_only_%d_to_%d_tcp" % (f_leo, t_leo)
            run_ml = "multilayer_%d_to_%d_tcp" % (f_ml, t_ml)
            cap_leo, _ = _read_cap_mbps_from_config(run_leo)
            cap_ml, _ = _read_cap_mbps_from_config(run_ml)
            tx_l, ty_l, path_l = _read_throughput_mbps_ts(run_leo)
            tx_m, ty_m, path_m = _read_throughput_mbps_ts(run_ml)
            if not ty_l or not ty_m:
                raise RuntimeError(
                    "Missing/empty throughput for %s: leo=%s multilayer=%s" % (desc, path_l, path_m)
                )
            tx_l, ty_l = _clip_series_to_time_s(tx_l, ty_l, args.duration_s)
            tx_m, ty_m = _clip_series_to_time_s(tx_m, ty_m, args.duration_s)
            peak_leo = float(np.max(ty_l))
            peak_ml = float(np.max(ty_m))
            rows.append(
                {
                    "desc": desc,
                    "run_leo": run_leo,
                    "run_ml": run_ml,
                    "peak_leo": peak_leo,
                    "peak_ml": peak_ml,
                    "cap_leo": cap_leo,
                    "cap_ml": cap_ml,
                }
            )
            print(
                "  %s: peak LEO=%.3f ML=%.3f Mb/s (caps %.3f / %.3f)"
                % (desc, peak_leo, peak_ml, cap_leo, cap_ml)
            )
    except Exception as e:
        print("ERROR:", str(e))
        return 1

    csv_path = args.out_prefix + "_peaks.csv"
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "description",
                "run_leo_only",
                "run_multilayer",
                "peak_throughput_mbps_leo_only",
                "peak_throughput_mbps_multilayer",
                "nominal_cap_mbps_leo_only",
                "nominal_cap_mbps_multilayer",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r["desc"],
                    r["run_leo"],
                    r["run_ml"],
                    "%.6f" % r["peak_leo"],
                    "%.6f" % r["peak_ml"],
                    "%.6f" % r["cap_leo"],
                    "%.6f" % r["cap_ml"],
                ]
            )
    print("Wrote:", csv_path)

    _plot_bars(rows, args.out_prefix, args.duration_s, args.time_step_ms, args.ylim_max)
    return 0


if __name__ == "__main__":
    sys.exit(main())
