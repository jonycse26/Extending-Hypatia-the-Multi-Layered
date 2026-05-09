#!/usr/bin/env python3
"""
Figure I — Long-path performance comparison

Objective:
  Show that MEO improves performance for long-distance communication.

Inputs:
  - avg_throughput_mbps
  - completion_time_s (panel (b) falls back to active_transfer_duration_s when incomplete)
  - avg_hop_count
  - path_available_ratio

Layout:
  Grouped bar chart over tiers:
    X-axis: short, medium, long
    Bars: LEO-only, Multilayer

Metrics come from ``runs/...`` (``extract_metrics`` + path availability). ``--duration-s`` /
``--time-step-ms`` annotate the figure for the intended simulation setup (default: match
``run_list``: 25 s, 1000 ms → ``dynamic_state_1000ms_for_25s``). Re-run experiment-3 ns-3 jobs
for that horizon so bars match the caption.
"""

import argparse
import csv
import glob
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "figure-i long-path comparison")
sys.path.insert(0, SCRIPT_DIR)

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment3_distance_tiers,
        experiment3_pairs_leo,
        experiment3_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list experiment3 / timing defaults: %s" % e)

try:
    from evaluation_utils import extract_metrics
except Exception as e:
    raise RuntimeError("Could not import evaluation_utils.extract_metrics: %s" % e)


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


def _load_schedule_from_to(run_dir):
    p = os.path.join(run_dir, "schedule.csv")
    if not os.path.isfile(p):
        return None, None
    with open(p, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 3:
                continue
            try:
                return int(parts[1]), int(parts[2])
            except ValueError:
                continue
    return None, None


def _path_available_ratio(run_dir):
    cfg = _parse_props(os.path.join(run_dir, "config_ns3.properties"))
    routes_rel = cfg.get("satellite_network_routes_dir")
    if not routes_rel:
        return float("nan")
    routes_dir = os.path.normpath(os.path.join(run_dir, routes_rel))
    if not os.path.isdir(routes_dir):
        return float("nan")

    from_id, to_id = _load_schedule_from_to(run_dir)
    if from_id is None or to_id is None:
        return float("nan")

    try:
        sim_end = int(cfg.get("simulation_end_time_ns", "0"))
    except ValueError:
        sim_end = 0

    fstates = []
    for fp in glob.glob(os.path.join(routes_dir, "fstate_*.txt")):
        base = os.path.basename(fp)
        try:
            t_ns = int(base.replace("fstate_", "").replace(".txt", ""))
        except ValueError:
            continue
        if sim_end <= 0 or t_ns <= sim_end:
            fstates.append((t_ns, fp))
    fstates.sort(key=lambda x: x[0])
    if not fstates:
        return float("nan")

    next_map = {}
    valid = 0
    total = 0
    max_hops = 80
    for _t, fp in fstates:
        with open(fp, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3:
                    continue
                try:
                    src = int(parts[0]); dst = int(parts[1]); nh = int(parts[2])
                except ValueError:
                    continue
                if dst == to_id:
                    next_map[src] = nh

        total += 1
        cur = next_map.get(from_id, -1)
        ok = False
        if cur != -1:
            for _ in range(max_hops):
                if cur == to_id:
                    ok = True
                    break
                nxt = next_map.get(cur, -1)
                if nxt == -1:
                    break
                cur = nxt
        if ok:
            valid += 1

    return float(valid) / float(total) if total > 0 else float("nan")


def _find_run_dir(from_id, to_id, tier, mode):
    """
    Prefer canonical experiment-3 folder: example3_distance_{tier}_{from}_to_{to}_tcp.

    Fallback (legacy): leo_only_* / multilayer_* for the same endpoints if present.
    """
    preferred = os.path.join(SCRIPT_DIR, "runs", "example3_distance_%s_%d_to_%d_tcp" % (tier, from_id, to_id))
    if os.path.isdir(preferred):
        return preferred
    if mode == "leo_only":
        legacy = os.path.join(SCRIPT_DIR, "runs", "leo_only_%d_to_%d_tcp" % (from_id, to_id))
        if os.path.isdir(legacy):
            return legacy
    else:
        legacy = os.path.join(SCRIPT_DIR, "runs", "multilayer_%d_to_%d_tcp" % (from_id, to_id))
        if os.path.isdir(legacy):
            return legacy
    matches = sorted(glob.glob(os.path.join(SCRIPT_DIR, "runs", "*_%d_to_%d_tcp" % (from_id, to_id))))
    return matches[0] if matches else None


def _to_float(v):
    try:
        return float(v)
    except Exception:
        return float("nan")


def main():
    parser = argparse.ArgumentParser(description="Plot Figure I long-path comparison.")
    parser.add_argument(
        "--out-prefix",
        default=os.path.join(OUT_DIR, "figure_i_long_path_comparison"),
        help="Output prefix (without extension).",
    )
    parser.add_argument(
        "--csv-out",
        default=os.path.join(OUT_DIR, "figure_i_long_path_comparison_values.csv"),
        help="Output CSV with extracted values.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Figure annotation: intended simulation length (runs should match). Default: run_list.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Figure annotation: dynamic state interval. Default: run_list.",
    )
    args = parser.parse_args()

    n_fstate = _expected_fstate_file_count(args.duration_s, args.time_step_ms)
    print(
        "Figure I: annotated for %d s sim, %d ms state updates; forwarding-state files ≈ %d."
        % (args.duration_s, args.time_step_ms, n_fstate)
    )
    title_suffix = " — %d s sim, %d ms state updates" % (args.duration_s, args.time_step_ms)

    rows = []
    tiers = list(experiment3_distance_tiers)
    leo_map = {tier: pair for tier, pair in zip(tiers, experiment3_pairs_leo)}
    ml_map = {tier: pair for tier, pair in zip(tiers, experiment3_pairs_multilayer)}

    for tier in tiers:
        for mode, pair_map in [("leo_only", leo_map), ("multilayer", ml_map)]:
            from_id, to_id, desc = pair_map[tier]
            run_dir = _find_run_dir(from_id, to_id, tier, mode)
            metrics = {
                "avg_throughput_mbps": float("nan"),
                "completion_time_s": float("nan"),
                "active_transfer_duration_s": float("nan"),
                "completion_or_active_s": float("nan"),
                "avg_hop_count": float("nan"),
                "path_available_ratio": float("nan"),
            }
            run_name = ""
            if run_dir and os.path.isdir(run_dir):
                run_name = os.path.basename(run_dir)
                met = extract_metrics(run_dir)
                metrics["avg_throughput_mbps"] = _to_float(met.get("avg_throughput_mbps"))
                metrics["completion_time_s"] = _to_float(met.get("completion_time_s"))
                metrics["active_transfer_duration_s"] = _to_float(met.get("active_transfer_duration_s"))
                c = metrics["completion_time_s"]
                a = metrics["active_transfer_duration_s"]
                metrics["completion_or_active_s"] = c if math.isfinite(c) else a
                metrics["avg_hop_count"] = _to_float(met.get("avg_hop_count"))
                metrics["path_available_ratio"] = _path_available_ratio(run_dir)

            rows.append(
                {
                    "tier": tier,
                    "mode": mode,
                    "pair": desc,
                    "run_name": run_name,
                    **metrics,
                }
            )
            if not run_dir:
                print(
                    "WARNING Figure I: missing run dir for %s tier=%s — expected runs/example3_distance_%s_%d_to_%d_tcp "
                    "(generate via step_1 with get_experiment3_distance_based_scenario_run_list; includes LEO-only)."
                    % (mode, tier, tier, from_id, to_id)
                )

    os.makedirs(os.path.dirname(os.path.abspath(args.csv_out)), exist_ok=True)
    with open(args.csv_out, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "tier",
                "mode",
                "pair",
                "run_name",
                "avg_throughput_mbps",
                "completion_time_s",
                "active_transfer_duration_s",
                "completion_or_active_s",
                "avg_hop_count",
                "path_available_ratio",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    # Build grouped bars
    x = np.arange(len(tiers))
    w = 0.36
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    metric_specs = [
        ("avg_throughput_mbps", "(a) Avg throughput (Mbps)", True),
        (
            "completion_or_active_s",
            "(b) Completion (s) or active span†",
            False,
        ),
        ("avg_hop_count", "(c) Avg hop count", False),
        ("path_available_ratio", "(d) Path available ratio", True),
    ]

    for ax, (key, title, higher_better) in zip(axes.flat, metric_specs):
        leo_y = []
        ml_y = []
        for t in tiers:
            leo_row = next((r for r in rows if r["tier"] == t and r["mode"] == "leo_only"), None)
            ml_row = next((r for r in rows if r["tier"] == t and r["mode"] == "multilayer"), None)
            leo_y.append(_to_float(leo_row.get(key) if leo_row else float("nan")))
            ml_y.append(_to_float(ml_row.get(key) if ml_row else float("nan")))

        leo_arr = np.asarray(leo_y, dtype=float)
        ml_arr = np.asarray(ml_y, dtype=float)
        ax.bar(x - w / 2, leo_arr, w, label="LEO-only", color="#1f77b4")
        ax.bar(x + w / 2, ml_arr, w, label="Multilayer", color="#2ca02c")
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(tiers)
        ax.grid(True, axis="y", linestyle=":", alpha=0.6)
        finite = np.concatenate([leo_arr[np.isfinite(leo_arr)], ml_arr[np.isfinite(ml_arr)]])
        if finite.size == 0:
            ax.set_ylim(0.0, 1.0)
            ax.text(
                0.5,
                0.5,
                "no data",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="gray",
            )
        else:
            hi = float(np.nanmax(finite))
            ax.set_ylim(0.0, max(hi * 1.15, 1e-6))
        ax.text(
            0.01,
            0.96,
            "higher better" if higher_better else "lower better",
            transform=ax.transAxes,
            va="top",
            fontsize=8,
        )
        if key == "completion_or_active_s":
            ax.text(
                0.5,
                -0.28,
                "†If the flow did not finish in-window, bar = first-byte→last sample (~observed span).",
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=7,
                color="0.35",
            )
    axes[0, 0].legend(loc="best")
    fig.suptitle("Figure I — Long-path performance comparison" + title_suffix, fontsize=14)
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)), exist_ok=True)
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)

    print("Wrote:", out_png)
    print("Wrote:", out_pdf)
    print("Wrote:", args.csv_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

