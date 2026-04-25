#!/usr/bin/env python3
"""
Figure Q — Link sharing / path overlap (LEO-only vs multilayer)

**Metric (option A):** For each physical link ``l`` (undirected hop between consecutive nodes
on a path, including satellite–satellite ISLs and satellite–GS hops):

  link_load(l) = number of directed GS→GS flows whose shortest-hop path (from forwarding
  state) traverses ``l``.

**Flows:** All ordered ground-station pairs (A→B), A ≠ B — same notion as Figure P
(constellation-wide demand proxy).

**Snapshot:** One merged ``fstate`` snapshot (default: middle timestep) so link_load is
well-defined for a single routing epoch.

**Plot:** ECDF of link_load over **utilized** links (load ≥ 1) — LEO-only vs multilayer.
High mass at large loads ⇒ more flows share the same links (congestion / overlap risk).

Also writes a summary CSV (max / mean / p95 load, count of links with load ≥ 2).

Prereq: ``fstate_*.txt`` under each run’s ``satellite_network_routes_dir``.
"""

import argparse
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(SCRIPT_DIR, "figure-q link sharing")
sys.path.insert(0, SCRIPT_DIR)

import evaluation_utils as eu  # noqa: E402
import plot_figure_p_gs_connectivity as figp  # noqa: E402

try:
    from run_list import (
        dynamic_state_update_interval_ms,
        experiment1_pairs_leo,
        experiment1_pairs_multilayer,
        simulation_end_time_s,
    )
except Exception as e:
    raise RuntimeError("Could not import run_list: %s" % e)


def _trace_path_nodes(fwd, a, b, max_hops=80):
    """Return node list for directed path a→b, or None if unreachable."""
    cur = fwd.get((a, b))
    if cur is None or cur == -1:
        return None
    nodes = [a, cur]
    if cur == b:
        return nodes
    for _ in range(max_hops):
        nxt = fwd.get((cur, b))
        if nxt is None or nxt == -1:
            return None
        nodes.append(nxt)
        if nxt == b:
            return nodes
        cur = nxt
    return None


def _undirected_edge(u, v):
    return (u, v) if u < v else (v, u)


def _link_loads_for_snapshot(fwd, ordered_pairs):
    """link_load[undirected_edge] = count of flows using that hop."""
    loads = {}
    for a, b in ordered_pairs:
        nodes = _trace_path_nodes(fwd, a, b)
        if not nodes or len(nodes) < 2:
            continue
        for i in range(len(nodes) - 1):
            e = _undirected_edge(nodes[i], nodes[i + 1])
            loads[e] = loads.get(e, 0) + 1
    return loads


def _ecdf_xy(values):
    v = np.asarray([x for x in values if x == x], dtype=float)
    if v.size == 0:
        return np.array([]), np.array([])
    v.sort()
    y = np.arange(1, v.size + 1, dtype=float) / v.size
    return v, y


def _summarize_loads(loads_dict):
    vals = np.asarray([float(c) for c in loads_dict.values() if c >= 1], dtype=float)
    if vals.size == 0:
        return {
            "n_utilized_links": 0,
            "max_load": float("nan"),
            "mean_load": float("nan"),
            "p95_load": float("nan"),
            "n_links_load_ge_2": 0,
        }
    return {
        "n_utilized_links": int(vals.size),
        "max_load": float(np.max(vals)),
        "mean_load": float(np.mean(vals)),
        "p95_load": float(np.percentile(vals, 95)),
        "n_links_load_ge_2": int(np.sum(vals >= 2)),
    }


def _run_setup(run_dir_abs):
    routes_dir, satnet_dir, cfg = figp._resolve_routes_and_satnet(run_dir_abs)
    if not routes_dir or not os.path.isdir(routes_dir):
        raise FileNotFoundError("Missing routes dir: %s" % routes_dir)
    if not satnet_dir or not os.path.isdir(satnet_dir):
        raise FileNotFoundError("Missing satellite_network_dir: %s" % satnet_dir)
    n_gs = figp._count_ground_stations(satnet_dir)
    if n_gs <= 0:
        raise RuntimeError("No ground stations in %s" % satnet_dir)
    _leo_n, total_sats, _x, _y = eu._get_satellite_counts_from_config(run_dir_abs)
    gs_ids = [total_sats + i for i in range(n_gs)]
    sim_end = figp._read_sim_end_ns(cfg)
    snapshots = figp._load_fstate_snapshots(routes_dir, sim_end)
    if not snapshots:
        raise FileNotFoundError("No fstate under %s" % routes_dir)
    return snapshots, gs_ids, cfg


def main():
    p = argparse.ArgumentParser(description="Figure Q: link sharing (path overlap) ECDF.")
    p.add_argument(
        "--leo-run",
        default=None,
        help="LEO-only TCP run dir (basename under runs/ or absolute). Default: first exp1 pair.",
    )
    p.add_argument(
        "--multilayer-run",
        default=None,
        help="Multilayer TCP run dir. Default: first exp1 multilayer pair.",
    )
    p.add_argument(
        "--snapshot-index",
        type=int,
        default=-1,
        help="Which merged fstate snapshot to use (0..T-1). Default -1 = middle.",
    )
    p.add_argument(
        "--out-prefix",
        default=os.path.join(FIGURE_DIR, "figure_q_link_sharing"),
        help="Output prefix (.png / .pdf / _summary.csv / _loads_*.csv).",
    )
    p.add_argument(
        "--duration-s",
        type=int,
        default=simulation_end_time_s,
        help="Caption: simulation length.",
    )
    p.add_argument(
        "--time-step-ms",
        type=int,
        default=dynamic_state_update_interval_ms,
        help="Caption: dynamic state interval.",
    )
    args = p.parse_args()

    f_lo, t_lo, _ = experiment1_pairs_leo[0]
    f_ml, t_ml, _ = experiment1_pairs_multilayer[0]
    leo_name = args.leo_run or ("leo_only_%d_to_%d_tcp" % (f_lo, t_lo))
    ml_name = args.multilayer_run or ("multilayer_%d_to_%d_tcp" % (f_ml, t_ml))

    def resolve(name):
        if os.path.isdir(name):
            return os.path.abspath(name)
        return os.path.join(SCRIPT_DIR, "runs", name)

    leo_path = resolve(leo_name)
    ml_path = resolve(ml_name)

    try:
        snaps_leo, gs_leo, _ = _run_setup(leo_path)
        snaps_ml, gs_ml, _ = _run_setup(ml_path)
    except Exception as e:
        print("ERROR:", e)
        return 1

    def pick_idx(snaps):
        if args.snapshot_index >= 0:
            return min(args.snapshot_index, len(snaps) - 1)
        return len(snaps) // 2

    i_leo = pick_idx(snaps_leo)
    i_ml = pick_idx(snaps_ml)
    t_ns_leo, fwd_leo = snaps_leo[i_leo]
    t_ns_ml, fwd_ml = snaps_ml[i_ml]

    pairs_leo = [(a, b) for a in gs_leo for b in gs_leo if a != b]
    pairs_ml = [(a, b) for a in gs_ml for b in gs_ml if a != b]

    loads_leo = _link_loads_for_snapshot(fwd_leo, pairs_leo)
    loads_ml = _link_loads_for_snapshot(fwd_ml, pairs_ml)

    vals_leo = list(loads_leo.values())
    vals_ml = list(loads_ml.values())

    sum_leo = _summarize_loads(loads_leo)
    sum_ml = _summarize_loads(loads_ml)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_prefix)), exist_ok=True)
    sum_path = args.out_prefix + "_summary.csv"
    with open(sum_path, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "mode",
                "snapshot_index",
                "time_ns",
                "n_directed_flows",
                "n_utilized_undirected_links",
                "max_link_load",
                "mean_link_load",
                "p95_link_load",
                "n_links_with_load_ge_2",
            ]
        )
        w.writerow(
            [
                "LEO-only",
                i_leo,
                t_ns_leo,
                len(pairs_leo),
                sum_leo["n_utilized_links"],
                sum_leo["max_load"],
                sum_leo["mean_load"],
                sum_leo["p95_load"],
                sum_leo["n_links_load_ge_2"],
            ]
        )
        w.writerow(
            [
                "Multilayer",
                i_ml,
                t_ns_ml,
                len(pairs_ml),
                sum_ml["n_utilized_links"],
                sum_ml["max_load"],
                sum_ml["mean_load"],
                sum_ml["p95_load"],
                sum_ml["n_links_load_ge_2"],
            ]
        )
    print("Wrote:", sum_path)

    # ECDF plot (utilized links: load >= 1)
    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    x1, y1 = _ecdf_xy(vals_leo)
    x2, y2 = _ecdf_xy(vals_ml)
    if x1.size:
        ax.step(
            np.concatenate([[x1[0]], x1]),
            np.concatenate([[0.0], y1]),
            where="post",
            color="#1f77b4",
            linewidth=2.0,
            label="LEO-only",
        )
    if x2.size:
        ax.step(
            np.concatenate([[x2[0]], x2]),
            np.concatenate([[0.0], y2]),
            where="post",
            color="#2ca02c",
            linewidth=2.0,
            label="Multilayer",
        )

    ax.set_xlabel(
        "Link load (number of directed GS→GS flows using the link)",
        fontsize=10,
    )
    ax.set_ylabel("ECDF (over utilized links)", fontsize=11)
    # No top title: keep only the figure content.
    ax.grid(True, linestyle=":", alpha=0.65)
    ax.legend(loc="lower right", fontsize=9)
    hi = 1.0
    for arr in (x1, x2):
        if arr.size:
            hi = max(hi, float(np.max(arr)))
    ax.set_xlim(0.5, max(hi * 1.08, 2.0))
    ax.set_ylim(0.0, 1.05)
    fig.tight_layout()

    out_png = args.out_prefix + ".png"
    out_pdf = args.out_prefix + ".pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_png)
    print("Wrote:", out_pdf)

    # Optional: dump top-loaded edges for each mode (cap rows)
    def dump_loads(path, loads, label, max_rows=40):
        rows = sorted(loads.items(), key=lambda kv: -kv[1])[:max_rows]
        with open(path, "w", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(["mode", "endpoint_u", "endpoint_v", "link_load"])
            for (u, v), c in rows:
                w.writerow([label, u, v, c])

    dump_loads(args.out_prefix + "_loads_top_leo.csv", loads_leo, "LEO-only")
    dump_loads(args.out_prefix + "_loads_top_multilayer.csv", loads_ml, "Multilayer")
    print("Wrote:", args.out_prefix + "_loads_top_leo.csv")
    print("Wrote:", args.out_prefix + "_loads_top_multilayer.csv")

    print(
        "LEO-only   max_load=%s mean=%s p95=%s  (utilized links %d)"
        % (sum_leo["max_load"], sum_leo["mean_load"], sum_leo["p95_load"], sum_leo["n_utilized_links"])
    )
    print(
        "Multilayer max_load=%s mean=%s p95=%s  (utilized links %d)"
        % (sum_ml["max_load"], sum_ml["mean_load"], sum_ml["p95_load"], sum_ml["n_utilized_links"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
