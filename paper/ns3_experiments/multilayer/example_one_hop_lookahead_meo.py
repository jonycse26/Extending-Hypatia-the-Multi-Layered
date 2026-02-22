#!/usr/bin/env python3
"""
Example: One-hop lookahead for MEO path calculation

At each node, the next hop is chosen by looking ONE hop ahead:
  score(neighbor) = edge_cost(curr, neighbor) + shortest_dist(neighbor, target)
  next_hop = argmin over neighbors of score(neighbor)

This matches algorithm_free_one_multi_layer.py:
  distance_m = edge(curr, neighbor) + dist_sat_net_without_gs[neighbor, target]
  next_hop = neighbor that minimizes distance_m

Two modes:
  1) Tiny synthetic graph (default) – quick demo.
  2) Real constellation – run_list.py pairs (1196,1221) Mumbai→Lima and (1221,1203) Lima→Karachi.
     Use: python3 example_one_hop_lookahead_meo.py --real [time_s]
     time_s default 2 (Mumbai→Lima uses MEO at 2s).
"""

import os
import sys
import math

# Add satgenpy to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../../satgenpy')))

# --- Tiny synthetic graph ---
LEO_NUM = 3
NODES = 5
EDGES = [
    (0, 1, 6000e3), (1, 2, 6000e3), (0, 3, 1500e3), (1, 3, 1800e3),
    (2, 4, 1600e3), (3, 4, 4000e3),
]


def build_synthetic_graph():
    INF = float("inf")
    n = NODES
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
    adj = [[] for _ in range(n)]
    for u, v, w in EDGES:
        dist[u][v] = dist[v][u] = w
        adj[u].append((v, w))
        adj[v].append((u, w))
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return adj, dist


def one_hop_lookahead(curr, target, adj, dist, via_meo=None):
    if curr == target:
        return None, 0
    effective_target = via_meo if via_meo is not None else target
    best_neighbor = None
    best_score = float("inf")
    for neighbor, edge_w in adj[curr]:
        d = dist[neighbor][effective_target]
        if math.isinf(d):
            continue
        score = edge_w + d
        if score < best_score:
            best_score = score
            best_neighbor = neighbor
    return best_neighbor, best_score


def run_synthetic_example():
    adj, dist = build_synthetic_graph()
    print("=" * 60)
    print("One-hop lookahead (synthetic graph)")
    print("=" * 60)
    print("Graph: LEO 0,1,2  ;  MEO 3,4")
    print("Edges (km):", [(u, v, int(w/1000)) for u, v, w in EDGES])
    print()
    best_meo, curr, dst = 4, 0, 2
    print("Scenario: source 0, destination 2, MEO gateway 4")
    print("One-hop lookahead from node 0 (target = MEO 4):")
    for neighbor, edge_w in adj[0]:
        d = dist[neighbor][best_meo]
        score = edge_w + d
        print("  neighbor {}: edge = {} km, dist(neighbor, 4) = {} km  =>  score = {} km".format(
            neighbor, int(edge_w/1000), int(d/1000), int(score/1000)))
    next_hop, score = one_hop_lookahead(0, dst, adj, dist, via_meo=best_meo)
    print("  => next_hop = {} (score = {} km)".format(next_hop, int(score/1000)))
    path = [0]
    cur = 0
    for target in [best_meo, dst]:
        while cur != target:
            next_hop, _ = one_hop_lookahead(cur, target, adj, dist, via_meo=None)
            if next_hop is None:
                break
            path.append(next_hop)
            cur = next_hop
    print("Path: ", " -> ".join(map(str, path)))
    print("Formula: next_hop = argmin_{neighbor} [ edge(curr, neighbor) + dist(neighbor, target) ]")
    print("=" * 60)


# ---------- Real constellation example (run_list.py pairs) ----------
CONSTELLATION_DIR = os.path.abspath(os.path.join(
    SCRIPT_DIR,
    '../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer'
))
# run_list.py experiment1_pairs_multilayer: Mumbai→Lima (1196, 1221), Lima→Karachi (1221, 1203)
REAL_PAIRS = [
    (1196, 1221, "Mumbai to Lima"),
    (1221, 1203, "Lima to Karachi"),
]


def trace_path(fstate_dict, from_id, to_id, max_hops=25):
    """Trace path from fstate: returns list of node IDs including GS endpoints."""
    if (from_id, to_id) not in fstate_dict or fstate_dict[(from_id, to_id)] == -1:
        return None
    path = [from_id]
    current = fstate_dict[(from_id, to_id)]
    hops = 0
    while current != to_id and current != -1 and hops < max_hops:
        path.append(current)
        if (current, to_id) not in fstate_dict:
            break
        next_hop = fstate_dict[(current, to_id)]
        if next_hop == to_id:
            path.append(to_id)
            break
        current = next_hop
        hops += 1
    if path[-1] != to_id:
        path.append(to_id)
    return path


def run_real_example(time_s=2.0):
    import networkx as nx
    from astropy import units as u
    from satgen.tles import read_tles
    from satgen.ground_stations import read_ground_stations_extended
    from satgen.description import read_description
    from satgen.isls import read_isls
    from satgen.distance_tools import distance_m_between_satellites

    if not os.path.isdir(CONSTELLATION_DIR):
        print("ERROR: Constellation dir not found:", CONSTELLATION_DIR)
        return 1

    description = read_description(os.path.join(CONSTELLATION_DIR, "description.txt"))
    leo_num_sats = int(description.get("leo_num_sats", 1156))
    max_isl_length_m = float(description.get("max_isl_length_m", 4e7))

    tles = read_tles(os.path.join(CONSTELLATION_DIR, "tles.txt"))
    satellites = tles["satellites"]
    epoch = tles["epoch"]
    num_sats = len(satellites)
    ground_stations = read_ground_stations_extended(os.path.join(CONSTELLATION_DIR, "ground_stations.txt"))
    gs_start_id = num_sats

    list_isls = read_isls(os.path.join(CONSTELLATION_DIR, "isls.txt"), num_sats)
    time_ns = int(time_s * 1e9)
    time = epoch + time_ns * u.ns

    # Build satellite graph at this time
    G = nx.Graph()
    for i in range(num_sats):
        G.add_node(i)
    for (a, b) in list_isls:
        sat_distance_m = distance_m_between_satellites(
            satellites[a], satellites[b], str(epoch), str(time)
        )
        G.add_edge(a, b, weight=sat_distance_m)

    import numpy as np
    dist_np = nx.floyd_warshall_numpy(G)
    dist_np = np.where(np.isfinite(dist_np), dist_np, np.inf)

    # Load fstate for this time step
    dynamic_dir = os.path.join(CONSTELLATION_DIR, "dynamic_state_1000ms_for_5s")
    fstate_file = os.path.join(dynamic_dir, "fstate_%d.txt" % time_ns)
    if not os.path.isfile(fstate_file):
        print("ERROR: fstate file not found:", fstate_file)
        return 1

    fstate_dict = {}
    with open(fstate_file, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 3:
                try:
                    src, dst, nh = int(parts[0]), int(parts[1]), int(parts[2])
                    fstate_dict[(src, dst)] = nh
                except (ValueError, IndexError):
                    pass

    def label(n):
        if n >= gs_start_id:
            gid = n - gs_start_id
            return "GS %s (%d)" % (ground_stations[gid]["name"][:12], n) if gid < len(ground_stations) else "GS(%d)" % n
        return "MEO %d" % n if n >= leo_num_sats else "LEO %d" % n

    print("=" * 70)
    print("One-hop lookahead – real constellation (run_list.py pairs)")
    print("=" * 70)
    print("Time: t = %.1f s" % time_s)
    print("LEO sats: 0 .. %d  |  MEO sats: %d .. %d  |  GS from %d" % (leo_num_sats - 1, leo_num_sats, num_sats - 1, gs_start_id))
    print()

    for from_id, to_id, name in REAL_PAIRS:
        path = trace_path(fstate_dict, from_id, to_id)
        if not path or len(path) < 2:
            print("[%s] %d -> %d: no path" % (name, from_id, to_id))
            print()
            continue

        print("-" * 70)
        print("%s  (GS %d -> GS %d)" % (name, from_id, to_id))
        print("Path: " + " -> ".join([label(p) for p in path]))
        print()

        # Satellite segment: path[1] .. path[-2] are satellites (path[0] and path[-1] are GS)
        sat_path = [p for p in path if isinstance(p, int) and p < num_sats]
        if len(sat_path) < 2:
            print("  (Single sat or no sat segment; one-hop lookahead N/A)")
            print()
            continue

        for idx in range(len(sat_path) - 1):
            curr = sat_path[idx]
            next_node = sat_path[idx + 1]
            target = next_node  # one-hop lookahead target = next waypoint (MEO gateway or dest LEO)
            neighbors_with_weights = list(G.neighbors(curr))
            if not neighbors_with_weights:
                continue
            # One-hop lookahead: score = edge(curr, n) + dist(n, target)
            best_n = None
            best_score = float("inf")
            scores = []
            for n in neighbors_with_weights:
                w = G.edges[(curr, n)]["weight"]
                d = float(dist_np[n, target])
                if math.isinf(d):
                    continue
                score = w + d
                scores.append((n, w, d, score))
                if score < best_score:
                    best_score = score
                    best_n = n
            print("  One-hop lookahead at %s (target = %s):" % (label(curr), label(target)))
            for n, w, d, score in sorted(scores, key=lambda x: x[3]):
                mark = " <-- chosen" if n == next_node else ""
                print("    neighbor %s: edge = %.0f km, dist(neighbor, target) = %.0f km  =>  score = %.0f km%s" % (
                    label(n), w / 1000, d / 1000, score / 1000, mark))
            print("    => next_hop = %s (score = %.0f km)" % (label(best_n), best_score / 1000))
            print()
        print()

    print("Formula: next_hop = argmin_{neighbor} [ edge(curr, neighbor) + dist(neighbor, target) ]")
    print("=" * 70)
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    use_real = "--real" in sys.argv
    time_s = 2.0
    if args:
        try:
            time_s = float(args[0])
        except ValueError:
            pass

    if use_real:
        return run_real_example(time_s)
    run_synthetic_example()
    return 0


if __name__ == "__main__":
    sys.exit(main())
