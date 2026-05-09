#!/usr/bin/env python3
"""
Figure P — Ground-station pair connectivity / reachability (LEO-only vs multilayer)

Uses merged forwarding snapshots ``fstate_*.txt`` under each run’s
``satellite_network_routes_dir`` (same cumulative merge as path reconstruction in
``evaluation_utils``).

**Per timestep t** (after merging deltas up to that file):

  connected_pair_ratio(t) = (# ordered GS pairs (A→B), A≠B, with a valid path) / (# all such pairs)

**Summaries**

  avg_connected_pair_ratio = mean_t connected_pair_ratio(t)

For each ordered pair (A, B):

  path_available_ratio_{A,B} = (# timesteps with valid A→B path) / (# timesteps)

  fully_connected_pair_fraction = (# pairs with path_available_ratio = 1) / (# all pairs)

**Plot (option A):** bar chart — LEO-only vs multilayer on the x-axis (grouped as two bars),
y-axis = avg_connected_pair_ratio.

Representative runs default to one experiment-1 pair each (any TCP run with the correct
``config_ns3.properties`` routes dir is sufficient; routing is constellation-wide, not
per-flow).

Prereq: generated dynamic state (``fstate_*.txt``) for both constellations (e.g. step_0 /
step_2 pipeline).
"""

import argparse
import csv
import glob
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-p gs connectivity")
sys.path.insert(0, SCRIPT_DIR)

import evaluation_utils as eu  # noqa: E402

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)


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


def _resolve_routes_and_satnet(run_dir_abs):
    cfg = _parse_props(os.path.join(run_dir_abs, "config_ns3.properties"))
    routes_rel = cfg.get("satellite_network_routes_dir")
    satnet_rel = cfg.get("satellite_network_dir")
    if not routes_rel:
        return None, None, cfg
    routes_dir = os.path.normpath(os.path.join(run_dir_abs, routes_rel))
    satnet_dir = (
        os.path.normpath(os.path.join(run_dir_abs, satnet_rel)) if satnet_rel else None
    )
    return routes_dir, satnet_dir, cfg


def _count_ground_stations(satnet_abs):
    p = os.path.join(satnet_abs, "ground_stations.txt")
    if not os.path.isfile(p):
        return 0
    n = 0
    with open(p, "r") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _read_sim_end_ns(cfg):
    try:
        return int(cfg.get("simulation_end_time_ns", "0"))
    except ValueError:
        return 0


def _load_fstate_snapshots(routes_dir, sim_end_ns):
    """List of (time_ns, cumulative_fwd_dict) with fwd[(src,dst)] = next_hop."""
    files = []
    for fp in glob.glob(os.path.join(routes_dir, "fstate_*.txt")):
        base = os.path.basename(fp)
        try:
            t_ns = int(base.replace("fstate_", "").replace(".txt", ""))
        except ValueError:
            continue
        if sim_end_ns > 0 and t_ns > sim_end_ns:
            continue
        files.append((t_ns, fp))
    files.sort(key=lambda x: x[0])
    cumulative = {}
    snapshots = []
    for t_ns, fp in files:
        with open(fp, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3:
                    continue
                try:
                    src = int(parts[0])
                    dst = int(parts[1])
                    nh = int(parts[2])
                except ValueError:
                    continue
                cumulative[(src, dst)] = nh
        snapshots.append((t_ns, dict(cumulative)))
    return snapshots


def _path_exists(fwd, a, b, max_hops=80):
    """Directed reachability a → b using entries (*, b) → next_hop."""
    cur = fwd.get((a, b))
    if cur is None or cur == -1:
        return False
    for _ in range(max_hops):
        if cur == b:
            return True
        nxt = fwd.get((cur, b))
        if nxt is None or nxt == -1:
            return False
        cur = nxt
    return False


def _compute_connectivity_metrics(snapshots, gs_ids):
    """
    gs_ids: list of ground station node IDs (e.g. total_sats .. total_sats+n-1).
    """
    ordered_pairs = [(a, b) for a in gs_ids for b in gs_ids if a != b]
    n_pairs = len(ordered_pairs)
    if n_pairs == 0 or not snapshots:
        return {
            "avg_connected_pair_ratio": float("nan"),
            "fully_connected_pair_fraction": float("nan"),
            "n_timesteps": len(snapshots),
            "n_gs": len(gs_ids),
            "n_ordered_pairs": n_pairs,
            "connected_pair_ratio_per_t": [],
        }

    connected_per_t = []
    for _t_ns, fwd in snapshots:
        ok = sum(1 for (a, b) in ordered_pairs if _path_exists(fwd, a, b))
        connected_per_t.append(ok / float(n_pairs))

    n_t = len(snapshots)
    ratios_per_pair = []
    for (a, b) in ordered_pairs:
        cnt = sum(1 for _t, fwd in snapshots if _path_exists(fwd, a, b))
        ratios_per_pair.append(cnt / float(n_t))

    fully = sum(1 for r in ratios_per_pair if r >= 1.0 - 1e-12)
    return {
        "avg_connected_pair_ratio": float(np.mean(connected_per_t)),
        "fully_connected_pair_fraction": fully / float(n_pairs),
        "n_timesteps": n_t,
        "n_gs": len(gs_ids),
        "n_ordered_pairs": n_pairs,
        "connected_pair_ratio_per_t": connected_per_t,
    }


def _analyze_run(run_dir_abs, label):
    routes_dir, satnet_dir, cfg = _resolve_routes_and_satnet(run_dir_abs)
    if not routes_dir or not os.path.isdir(routes_dir):
        raise FileNotFoundError("Missing routes dir for %s: %s" % (label, routes_dir))
    if not satnet_dir or not os.path.isdir(satnet_dir):
        raise FileNotFoundError("Missing satellite_network_dir for %s: %s" % (label, satnet_dir))

    n_gs = _count_ground_stations(satnet_dir)
    if n_gs <= 0:
        raise RuntimeError("No ground_stations.txt entries under %s" % satnet_dir)

    _leo_n, total_sats, _m1, _m2 = eu._get_satellite_counts_from_config(run_dir_abs)
    gs_ids = [total_sats + i for i in range(n_gs)]

    sim_end = _read_sim_end_ns(cfg)
    snapshots = _load_fstate_snapshots(routes_dir, sim_end)
    if not snapshots:
        raise FileNotFoundError("No fstate_*.txt under %s" % routes_dir)

    m = _compute_connectivity_metrics(snapshots, gs_ids)
    m["label"] = label
    m["run_dir"] = run_dir_abs
    m["routes_dir"] = routes_dir
    return m


def main():
    p = argparse.ArgumentParser(description="Figure P: GS-pair connectivity (avg connected-pair ratio).")
    p.add_argument(
        "--leo-run",
        default=None,
        help="LEO-only TCP run directory (basename under runs/ or absolute). Default: first exp1 leo_only pair.",
    )
    p.add_argument(
        "--multilayer-run",
        default=None,
        help="Multilayer TCP run directory. Default: first exp1 multilayer pair.",
    )
    p.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_p_gs_connectivity"),
        help="Output prefix (.png / .pdf / _summary.csv).",
    )
    p.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Caption: simulation length (should match fstate horizon).",
    )
    p.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Caption: dynamic state interval.",
    )
    args = p.parse_args()

    f_lo, t_lo, _d = experiment1_pairs_leo[0]
    f_ml, t_ml, _d2 = experiment1_pairs_multilayer[0]
    leo_name = args.leo_run or ("leo_only_%d_to_%d_tcp" % (f_lo, t_lo))
    ml_name = args.multilayer_run or ("multilayer_%d_to_%d_tcp" % (f_ml, t_ml))

    def resolve(name):
        if os.path.isdir(name):
            return os.path.abspath(name)
        return os.path.join(SCRIPT_DIR, "runs", name)

    leo_path = resolve(leo_name)
    ml_path = resolve(ml_name)

    try:
        m_leo = _analyze_run(leo_path, "LEO-only")
        m_ml = _analyze_run(ml_path, "Multilayer")
    except Exception as e:
        print("ERROR:", e)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out_prefix)), exist_ok=True)
    summary_path = args.out_prefix + "_summary.csv"
    with open(summary_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "mode",
                "run_dir",
                "n_gs",
                "n_ordered_pairs",
                "n_timesteps",
                "avg_connected_pair_ratio",
                "fully_connected_pair_fraction",
            ]
        )
        for m in (m_leo, m_ml):
            w.writerow(
                [
                    m["label"],
                    m["run_dir"],
                    m["n_gs"],
                    m["n_ordered_pairs"],
                    m["n_timesteps"],
                    "%.10f" % m["avg_connected_pair_ratio"],
                    "%.10f" % m["fully_connected_pair_fraction"],
                ]
            )
    print("Wrote:", summary_path)

    # Optional: per-timestep series
    ts_path = args.out_prefix + "_connected_ratio_per_timestep.csv"
    with open(ts_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["timestep_index", "connected_pair_ratio_leo_only", "connected_pair_ratio_multilayer"])
        n = max(len(m_leo["connected_pair_ratio_per_t"]), len(m_ml["connected_pair_ratio_per_t"]))
        for i in range(n):
            yl = m_leo["connected_pair_ratio_per_t"][i] if i < len(m_leo["connected_pair_ratio_per_t"]) else ""
            ym = m_ml["connected_pair_ratio_per_t"][i] if i < len(m_ml["connected_pair_ratio_per_t"]) else ""
            w.writerow([i, yl, ym])
    print("Wrote:", ts_path)

    # --- Plot option A: two bars, y = avg connected pair ratio
    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    x = np.arange(2)
    heights = [m_leo["avg_connected_pair_ratio"], m_ml["avg_connected_pair_ratio"]]
    colors = ["#1f77b4", "#2ca02c"]
    labels = ["LEO-only", "Multilayer"]
    bars = ax.bar(x, heights, width=0.55, color=colors, edgecolor="#333333", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Average connected-pair ratio", fontsize=11)
    finite_h = [h for h in heights if h == h and np.isfinite(h)]
    y_hi = min(1.05, max(0.12, float(np.max(finite_h)) * 1.18)) if finite_h else 1.0
    ax.set_ylim(0.0, y_hi)
    ax.grid(True, axis="y", linestyle=":", alpha=0.65)
    ax.set_title(
        "Figure P — GS-pair reachability (ordered pairs)\n"
        "mean over time of (pairs with valid path) / (all GS pairs)"
        + " — %d s sim, %d ms updates · %d GS, %d directed pairs · %d timesteps"
        % (
            args.duration_s,
            args.time_step_ms,
            m_leo["n_gs"],
            m_leo["n_ordered_pairs"],
            m_leo["n_timesteps"],
        ),
        fontsize=10,
    )

    for b, h, m in zip(bars, heights, (m_leo, m_ml)):
        ax.text(
            b.get_x() + b.get_width() / 2,
            min(h + 0.02, ax.get_ylim()[1] * 0.98),
            "%.4f" % h,
            ha="center",
            va="bottom",
            fontsize=9,
        )

    foot = (
        "Fully connected (path in every timestep): LEO-only %.2f%% · Multilayer %.2f%% of directed pairs"
        % (
            100.0 * m_leo["fully_connected_pair_fraction"],
            100.0 * m_ml["fully_connected_pair_fraction"],
        )
    )
    fig.text(0.5, 0.02, foot, ha="center", fontsize=8, color="0.35")

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)

    print(
        "LEO-only   avg_connected_pair_ratio=%.6f  fully_connected_pair_fraction=%.6f"
        % (m_leo["avg_connected_pair_ratio"], m_leo["fully_connected_pair_fraction"])
    )
    print(
        "Multilayer avg_connected_pair_ratio=%.6f  fully_connected_pair_fraction=%.6f"
        % (m_ml["avg_connected_pair_ratio"], m_ml["fully_connected_pair_fraction"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
