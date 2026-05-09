#!/usr/bin/env python3
"""
Figure L — Load curve (LEO-only vs Multilayer)

Goal:
  x-axis: offered load (Mbps per ISL/GSL from each run’s config, or an explicit column
          in the manifest — use distinct ns-3 runs per load level, e.g. different
          ``data_rate_megabit_per_s`` or multi-flow scenarios).
  y-axis: delivered throughput, mean RTT, and completion / active transfer span — showing
          LEO-only collapsing faster under stress while multilayer degrades more slowly
          (requires ≥2 load points; regenerate metrics after new runs).

Inputs:
  1. Manifest CSV (see ``figure-l load-curve/figure_l_load_curve_runs.csv``): columns
     ``offered_load_mbps`` (optional), ``leo_tcp_run``, ``multilayer_tcp_run``.
     If ``offered_load_mbps`` is empty, ``isl_data_rate_megabit_per_s`` is read from
     the LEO run’s ``config_ns3.properties`` under ``runs/``.
  2. Aggregates from ``multilayer_all_experiments_metrics.csv`` (join on ``run_name``).

Regenerate metrics:
  ``python3 export_multilayer_metrics_table.py``
"""

import argparse
import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(SCRIPT_DIR, "runs")
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-l load-curve")
DEFAULT_MANIFEST = os.path.join(OUT_DIR, "figure_l_load_curve_runs.csv")
DEFAULT_METRICS = os.path.join(SCRIPT_DIR, "multilayer_all_experiments_metrics.csv")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list timing defaults: %s" % e)


def _expected_fstate_file_count(duration_s, time_step_ms):
    if duration_s < 0 or time_step_ms <= 0:
        return 0
    return (duration_s * 1000) // time_step_ms + 1


def _parse_props(path):
    props = {}
    if not os.path.isfile(path):
        return props
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                v = v[1:-1]
            props[k.strip()] = v.strip()
    return props


def _offered_mbps_from_run_dir(run_name):
    """Use isl_data_rate_megabit_per_s from runs/<run>/config_ns3.properties."""
    cfg = os.path.join(RUNS_DIR, run_name, "config_ns3.properties")
    props = _parse_props(cfg)
    raw = props.get("isl_data_rate_megabit_per_s")
    if raw is None:
        return float("nan")
    try:
        return float(raw)
    except ValueError:
        return float("nan")


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def _load_metrics_rows(metrics_path):
    by = {}
    with open(metrics_path, "r") as f:
        for r in csv.DictReader(f):
            rn = (r.get("run_name") or "").strip()
            if rn.endswith("_tcp"):
                by[rn] = r
    return by


def _load_manifest(manifest_path):
    rows = []
    with open(manifest_path, "r") as f:
        for r in csv.DictReader(f):
            lo = (r.get("leo_tcp_run") or "").strip()
            ml = (r.get("multilayer_tcp_run") or "").strip()
            if not lo or not ml:
                continue
            ol_raw = (r.get("offered_load_mbps") or "").strip()
            ol = _to_float(ol_raw) if ol_raw else float("nan")
            rows.append({"offered_load_mbps": ol, "leo_tcp_run": lo, "multilayer_tcp_run": ml})
    return rows


def _resolve_loads(manifest_rows):
    out = []
    for r in manifest_rows:
        ol = r["offered_load_mbps"]
        if not math.isfinite(ol):
            ol = _offered_mbps_from_run_dir(r["leo_tcp_run"])
        out.append(
            {
                "offered_load_mbps": ol,
                "leo_tcp_run": r["leo_tcp_run"],
                "multilayer_tcp_run": r["multilayer_tcp_run"],
            }
        )
    return out


def _metric_from_row(row, key, alt_keys=()):
    if not row:
        return float("nan")
    v = _to_float(row.get(key))
    if math.isfinite(v):
        return v
    for k in alt_keys:
        v = _to_float(row.get(k))
        if math.isfinite(v):
            return v
    return float("nan")


def _completion_display(row):
    """Prefer completion_time_s; else active_transfer_duration_s if exported."""
    c = _metric_from_row(row, "completion_time_s")
    if math.isfinite(c):
        return c
    return _metric_from_row(row, "active_transfer_duration_s")


def _plot_panels(xs, series, ylabels, titles, suptitle, out_prefix, time_suffix):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.0))
    for ax, (y_leo, y_ml), ylab, ttl in zip(axes, series, ylabels, titles):
        ax.plot(xs, y_leo, "o--", color="#1f77b4", lw=2.0, ms=7, label="LEO-only")
        ax.plot(xs, y_ml, "s-", color="#2ca02c", lw=2.0, ms=7, label="Multilayer")
        ax.set_xlabel("Offered load (ISL/GSL Mbps, per config)")
        ax.set_ylabel(ylab)
        ax.set_title(ttl, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.65)
        ax.legend(loc="best", fontsize=8)
    fig.suptitle(suptitle + time_suffix, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    out_png = out_prefix + ".png"
    out_pdf = out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


def main():
    parser = argparse.ArgumentParser(description="Plot Figure L — load curve (LEO vs Multilayer).")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="CSV: offered_load_mbps?, leo_tcp_run, multilayer_tcp_run")
    parser.add_argument("--metrics-csv", default=DEFAULT_METRICS, help="multilayer_all_experiments_metrics.csv")
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(OUT_DIR, "figure_l_load_curve"),
        help="Output path prefix (no extension).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Caption: intended sim length. Default: run_list.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Caption: dynamic state interval. Default: run_list.",
    )
    parser.add_argument(
        "--with-isl-panel",
        action="store_true",
        help="If set, write a second figure with LEO–LEO peak ISL util vs load (4th metric).",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure L: caption %d s sim, %d ms state updates; fstate files ≈ %d."
        % (args.duration_s, args.time_step_ms, n_fstate)
    )
    time_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)

    if not os.path.isfile(args.manifest):
        print("ERROR: manifest not found:", args.manifest)
        print("  Create it with columns: offered_load_mbps (optional), leo_tcp_run, multilayer_tcp_run")
        return 1
    if not os.path.isfile(args.metrics_csv):
        print("ERROR: metrics CSV not found:", args.metrics_csv)
        return 1

    manifest = _resolve_loads(_load_manifest(args.manifest))
    if not manifest:
        print("ERROR: no valid rows in manifest.")
        return 1

    metrics_by = _load_metrics_rows(args.metrics_csv)

    records = []
    for i, row in enumerate(manifest):
        lo, ml = row["leo_tcp_run"], row["multilayer_tcp_run"]
        x = row["offered_load_mbps"]
        rlo, rml = metrics_by.get(lo), metrics_by.get(ml)
        if not rlo or not rml:
            print(
                "ERROR: missing metrics for row %d: %s / %s (re-run export_multilayer_metrics_table.py)"
                % (i + 1, lo, ml)
            )
            return 1
        if not math.isfinite(x):
            print(
                "ERROR: could not resolve offered_load_mbps for row %d (%s); set manifest column or fix config."
                % (i + 1, lo)
            )
            return 1
        records.append(
            {
                "offered_load_mbps": x,
                "leo_tcp_run": lo,
                "multilayer_tcp_run": ml,
                "thr_leo": _metric_from_row(rlo, "avg_throughput_mbps"),
                "thr_ml": _metric_from_row(rml, "avg_throughput_mbps"),
                "rtt_leo": _metric_from_row(rlo, "avg_rtt_ms"),
                "rtt_ml": _metric_from_row(rml, "avg_rtt_ms"),
                "cmp_leo": _completion_display(rlo),
                "cmp_ml": _completion_display(rml),
                "util_leo": _metric_from_row(rlo, "leo_leo_isl_max_util"),
                "util_ml": _metric_from_row(rml, "leo_leo_isl_max_util"),
            }
        )

    records.sort(key=lambda r: r["offered_load_mbps"])
    xs = [r["offered_load_mbps"] for r in records]
    thr_leo = [r["thr_leo"] for r in records]
    thr_ml = [r["thr_ml"] for r in records]
    rtt_leo = [r["rtt_leo"] for r in records]
    rtt_ml = [r["rtt_ml"] for r in records]
    cmp_leo = [r["cmp_leo"] for r in records]
    cmp_ml = [r["cmp_ml"] for r in records]
    util_leo = [r["util_leo"] for r in records]
    util_ml = [r["util_ml"] for r in records]

    uq = set(xs)
    if len(uq) < 2:
        print(
            "WARNING: Figure L needs ≥2 distinct offered-load points for a proper curve; "
            "append rows in the manifest after running additional TCP scenarios (e.g. higher Mbps or more flows)."
        )

    os.makedirs(OUT_DIR, exist_ok=True)

    _plot_panels(
        xs,
        [(thr_leo, thr_ml), (rtt_leo, rtt_ml), (cmp_leo, cmp_ml)],
        ["Delivered throughput (Mbps)", "Mean RTT (ms)", "Completion or active span (s)"],
        [
            "(a) Throughput vs offered load",
            "(b) RTT vs offered load",
            "(c) Completion / span vs load",
        ],
        "Figure L — Load curve (LEO-only vs Multilayer)",
        args.out_prefix,
        time_suffix,
    )

    csv_out = args.out_prefix + "_values.csv"
    with open(csv_out, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "offered_load_mbps",
                "leo_tcp_run",
                "multilayer_tcp_run",
                "throughput_leo_mbps",
                "throughput_multilayer_mbps",
                "avg_rtt_leo_ms",
                "avg_rtt_multilayer_ms",
                "completion_or_span_leo_s",
                "completion_or_span_multilayer_s",
                "leo_leo_isl_max_util_leo",
                "leo_leo_isl_max_util_multilayer",
            ]
        )
        for i, rec in enumerate(records):
            w.writerow(
                [
                    xs[i],
                    rec["leo_tcp_run"],
                    rec["multilayer_tcp_run"],
                    thr_leo[i],
                    thr_ml[i],
                    rtt_leo[i],
                    rtt_ml[i],
                    cmp_leo[i],
                    cmp_ml[i],
                    util_leo[i],
                    util_ml[i],
                ]
            )
    print("Wrote:", csv_out)

    if args.with_isl_panel:
        fig, ax = plt.subplots(figsize=(6.5, 5.0))
        ax.plot(xs, util_leo, "o--", color="#1f77b4", lw=2.0, ms=7, label="LEO-only")
        ax.plot(xs, util_ml, "s-", color="#2ca02c", lw=2.0, ms=7, label="Multilayer")
        ax.set_xlabel("Offered load (ISL/GSL Mbps, per config)")
        ax.set_ylabel("Peak LEO–LEO ISL utilization")
        ax.set_title("Figure L (detail) — LEO mesh peak utilization vs load" + time_suffix)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, linestyle=":", alpha=0.65)
        ax.legend(loc="best")
        fig.tight_layout()
        p2 = args.out_prefix + "_leo_leo_isl_peak"
        fig.savefig(p2 + ".png", dpi=220, bbox_inches="tight")
        fig.savefig(p2 + ".pdf", bbox_inches="tight")
        plt.close(fig)
        print("Wrote:", p2 + ".png")

    return 0


if __name__ == "__main__":
    sys.exit(main())
