# this is the algorithm for the free one multi-layer (LEO+MEO as two separate subgraphs)
#
# Case A: curr == dst_sat  -> go to GS
# Case B: curr is LEO and use_meo == True:
#         Step 1: enter a reachable MEO (via some LEO handoff that has a cross-layer edge)
#         Step 2: ensure that entry MEO can reach a gateway MEO (MEO-only)
#         Then inside MEO: route to gateway, then exit to dst_sat
# Case C: curr is LEO and use_meo == False -> LEO-only routing to dst_sat


from .fstate_calculation import *
import math
import networkx as nx


def algorithm_free_one_multi_layer(
        output_dynamic_state_dir,
        time_since_epoch_ns,
        satellites,
        ground_stations,
        sat_net_graph_only_satellites_with_isls,
        ground_station_satellites_in_range,
        num_isls_per_sat,
        sat_neighbor_to_if,
        list_gsl_interfaces_info,
        prev_output,
        enable_verbose_logs,
        leo_num_sats,
        meo_threshold_distance_m=10000000.0,
        meo_threshold_hops=3,
        path_diversity_epsilon_ratio=0.10,
        num_time_steps_for_diversity=6
):
    # Path diversity: we take the top-k next-hop options 
    def is_leo(sid: int) -> bool:
        return sid < leo_num_sats

    def is_meo(sid: int) -> bool:
        return sid >= leo_num_sats

    # Time-step index (0, 1, 2, ... per 1s step) for round-robin path selection
    _time_step_index = time_since_epoch_ns // 1_000_000_000

    def pick_best_tiebreak(candidates):
        """Take top-k by score (within epsilon), round-robin by time step."""
        if not candidates:
            return None
        best_score = min(s for s, _ in candidates)
        threshold = best_score * (1.0 + path_diversity_epsilon_ratio) if path_diversity_epsilon_ratio > 0 and best_score > 0 else best_score
        within = sorted([(s, n) for s, n in candidates if s <= threshold], key=lambda x: (x[0], x[1]))
        k = min(num_time_steps_for_diversity, len(within))
        top_k_nodes = [n for _, n in within[:k]]
        return top_k_nodes[_time_step_index % len(top_k_nodes)]

    def drop_2cycle_candidates(candidates, curr_node, dst_gs_node_id, fstate_dict):
        """Remove candidates n where n already forwards back to curr_node (avoids LEO 2-cycles e.g. 46<->80)."""
        filtered = [(s, n) for s, n in candidates if fstate_dict.get((n, dst_gs_node_id), (-1, -1, -1))[0] != curr_node]
        return filtered if filtered else candidates

    if enable_verbose_logs:
        print("\nALGORITHM: FREE ONE MULTI-LAYER (LEO/MEO subgraphs)")
        print("  > LEO satellites: 0 to %d" % (leo_num_sats - 1))
        print("  > MEO satellites: %d to %d" % (leo_num_sats, len(satellites) - 1))
        print("  > MEO threshold distance: %.2f km" % (meo_threshold_distance_m / 1000.0))
        print("  > MEO threshold hops: %d" % meo_threshold_hops)

    # ----------------------------
    # Graph sanity
    # ----------------------------
    if sat_net_graph_only_satellites_with_isls.number_of_nodes() != len(satellites):
        raise ValueError("Number of nodes in the graph does not match the number of satellites")
    for sid in range(len(satellites)):
        for n in sat_net_graph_only_satellites_with_isls.neighbors(sid):
            if n >= len(satellites):
                raise ValueError("Graph cannot contain satellite-to-ground-station links")

    # ----------------------------
    # Split into subgraphs
    # ----------------------------
    leo_nodes = list(range(0, leo_num_sats))
    meo_nodes = list(range(leo_num_sats, len(satellites)))

    leo_subgraph = sat_net_graph_only_satellites_with_isls.subgraph(leo_nodes).copy()
    meo_subgraph = sat_net_graph_only_satellites_with_isls.subgraph(meo_nodes).copy()

    # Cross-layer edges: LEO -> [(MEO, weight)]
    leo_to_meo_neighbors = {l: [] for l in leo_nodes}
    for l in leo_nodes:
        for n in sat_net_graph_only_satellites_with_isls.neighbors(l):
            if is_meo(n):
                w = sat_net_graph_only_satellites_with_isls.edges[(l, n)]["weight"]
                leo_to_meo_neighbors[l].append((n, w))

    # Safer distances: dict-of-dict shortest path lengths inside each subgraph
    dist_leo = dict(nx.all_pairs_dijkstra_path_length(leo_subgraph, weight="weight"))
    dist_meo = dict(nx.all_pairs_dijkstra_path_length(meo_subgraph, weight="weight"))

    # Real hop counts (unweighted)
    hop_leo = dict(nx.all_pairs_shortest_path_length(leo_subgraph))
    hop_meo = dict(nx.all_pairs_shortest_path_length(meo_subgraph))

    def d_leo(a: int, b: int) -> float:
        return dist_leo.get(a, {}).get(b, float("inf"))

    def d_meo(a: int, b: int) -> float:
        return dist_meo.get(a, {}).get(b, float("inf"))

    # ----------------------------
    # Helper: pick a gateway MEO for a given dst_sat, reachable from a MEO node
    # gateway = MEO node that has a direct edge to dst_sat
    # ----------------------------
    def pick_gateway_from_meo(meo_from: int, dst_sat: int):
        best_g = None
        best_key = (float("inf"), float("inf"))  

        for g in meo_nodes:
            if not sat_net_graph_only_satellites_with_isls.has_edge(g, dst_sat):
                continue  

            try:
                h = hop_meo[meo_from][g]
            except KeyError:
                continue  

            exit_w = sat_net_graph_only_satellites_with_isls.edges[(g, dst_sat)]["weight"]
            key = (float(h), float(exit_w))
            if key < best_key:
                best_key = key
                best_g = g

        return best_g

    # ----------------------------
    # Helper: cost from a MEO node to a LEO dst_sat via a gateway
    # (used only for picking dst_sat candidates for a GS when curr is MEO)
    # ----------------------------
    def meo_to_leo_cost(curr_meo: int, dst_sat: int) -> float:
        best = float("inf")
        for g in meo_nodes:
            if not sat_net_graph_only_satellites_with_isls.has_edge(g, dst_sat):
                continue
            dm = d_meo(curr_meo, g)
            if math.isinf(dm):
                continue
            w_exit = sat_net_graph_only_satellites_with_isls.edges[(g, dst_sat)]["weight"]
            best = min(best, dm + w_exit)
        return best

    #################################
    # BANDWIDTH STATE
    #################################
    output_filename = output_dynamic_state_dir + "/gsl_if_bandwidth_" + str(time_since_epoch_ns) + ".txt"
    if enable_verbose_logs:
        print("  > Writing interface bandwidth state to: " + output_filename)

    with open(output_filename, "w+") as f_out:
        if time_since_epoch_ns == 0:
            for node_id in range(len(satellites)):
                f_out.write("%d,%d,%f\n" % (
                    node_id, num_isls_per_sat[node_id],
                    list_gsl_interfaces_info[node_id]["aggregate_max_bandwidth"]
                ))
            for node_id in range(len(satellites), len(satellites) + len(ground_stations)):
                f_out.write("%d,%d,%f\n" % (
                    node_id, 0, list_gsl_interfaces_info[node_id]["aggregate_max_bandwidth"]
                ))

    #################################
    # FORWARDING STATE
    #################################
    prev_fstate = None
    if prev_output is not None:
        prev_fstate = prev_output["fstate"]

    gid_to_sat_gsl_if_idx = [0] * len(ground_stations)

    fstate = {}
    output_filename = output_dynamic_state_dir + "/fstate_" + str(time_since_epoch_ns) + ".txt"
    if enable_verbose_logs:
        print("  > Writing forwarding state to: " + output_filename)

    def if_pair(a: int, b: int):
        """Return (out_if, in_if) for edge (a,b), or None if either mapping is missing (e.g. cross-layer)."""
        out_if = sat_neighbor_to_if.get((a, b), -1)
        in_if = sat_neighbor_to_if.get((b, a), -1)
        return (out_if, in_if) if out_if != -1 and in_if != -1 else None

    with open(output_filename, "w+") as f_out:

        dist_satellite_to_ground_station = {}

        # ----------------------------
        # SATELLITE -> GS
        # Process curr in REVERSE order so the smaller-index node sees the larger's next_hop
        # and can avoid choosing it 
        # ----------------------------
        for curr in range(len(satellites) - 1, -1, -1):
            for dst_gid in range(len(ground_stations)):

                dst_gs_node_id = len(satellites) + dst_gid

                # Destination GS can connect only to LEO sats
                possible_dst_sats = []
                for gsl_dist_m, sat_id in ground_station_satellites_in_range[dst_gid]:
                    if is_leo(sat_id):
                        possible_dst_sats.append((gsl_dist_m, sat_id))

                # Pick destination-side LEO satellite dst_sat minimizing:
                # cost(curr -> dst_sat) + gsl(dst_sat -> GS)
                # - if curr is LEO: LEO-only distance
                # - if curr is MEO: MEO->gateway->dst_sat
                possibilities = []
                for gsl_dist_m, sat_id in possible_dst_sats:
                    if is_leo(curr):
                        d = d_leo(curr, sat_id)
                    else:
                        d = meo_to_leo_cost(curr, sat_id)

                    if math.isinf(d):
                        continue
                    possibilities.append((d + gsl_dist_m, sat_id))
                possibilities.sort()

                next_hop_decision = (-1, -1, -1)
                distance_to_ground_station_m = float("inf")

                if possibilities:
                    dst_sat = possibilities[0][1]
                    distance_to_ground_station_m = possibilities[0][0]

                    # Decide whether to use MEO 
                    use_meo = False
                    if is_leo(curr):
                        if distance_to_ground_station_m > meo_threshold_distance_m:
                            use_meo = True
                        else:
                            # hop count inside LEO subgraph
                            hops = hop_leo.get(curr, {}).get(dst_sat, float("inf"))
                            if not math.isinf(hops) and hops > meo_threshold_hops:
                                use_meo = True

                    # ============================================================
                    # CASE A: curr == dst_sat -> next hop is GS via GSL
                    # ============================================================
                    if curr == dst_sat:
                        next_hop_decision = (
                            dst_gs_node_id,
                            num_isls_per_sat[dst_sat] + gid_to_sat_gsl_if_idx[dst_gid],
                            0
                        )

                    # ============================================================
                    # CASE C: curr is LEO and use_meo == False -> LEO-only to dst_sat
                    # ============================================================
                    elif is_leo(curr) and not use_meo:
                        candidates = []
                        for neighbor_id in leo_subgraph.neighbors(curr):
                            score = (
                                leo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                + d_leo(neighbor_id, dst_sat)
                            )
                            candidates.append((score, neighbor_id))
                        candidates = drop_2cycle_candidates(candidates, curr, dst_gs_node_id, fstate)
                        best_next = pick_best_tiebreak(candidates)

                        if best_next is not None:
                            next_hop_decision = (
                                best_next,
                                sat_neighbor_to_if[(curr, best_next)],
                                sat_neighbor_to_if[(best_next, curr)]
                            )

                    # ============================================================
                    # CASE B
                    # ============================================================
                    else:
                        # -----------------------
                        #  curr is LEO: choose (handoff LEO) + (entry MEO) with gateway reachability
                        # -----------------------
                        if is_leo(curr):
                            best_handoff_leo = None
                            best_entry_meo = None
                            best_key = (float("inf"), float("inf"), float("inf"))  

                            # choose a LEO handoff node l, then cross-layer edge l->m
                            for l in leo_nodes:
                                d_curr_to_l = d_leo(curr, l)
                                if math.isinf(d_curr_to_l):
                                    continue

                                for m, w_lm in leo_to_meo_neighbors.get(l, []):
                                    g = pick_gateway_from_meo(m, dst_sat)
                                    if g is None:
                                        continue

                                    try:
                                        hop_m_to_g = hop_meo[m][g]
                                    except KeyError:
                                        continue

                                    exit_w = sat_net_graph_only_satellites_with_isls.edges[(g, dst_sat)]["weight"]
                                    entry_cost = d_curr_to_l + w_lm
                                    key = (entry_cost, float(hop_m_to_g), float(exit_w))

                                    if key < best_key:
                                        best_key = key
                                        best_handoff_leo = l
                                        best_entry_meo = m

                            # fallback if no valid entry -> LEO-only 
                            if best_entry_meo is None or best_handoff_leo is None:
                                candidates = []
                                for neighbor_id in leo_subgraph.neighbors(curr):
                                    score = (
                                        leo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                        + d_leo(neighbor_id, dst_sat)
                                    )
                                    candidates.append((score, neighbor_id))
                                candidates = drop_2cycle_candidates(candidates, curr, dst_gs_node_id, fstate)
                                best_next = pick_best_tiebreak(candidates)

                                if best_next is not None:
                                    next_hop_decision = (
                                        best_next,
                                        sat_neighbor_to_if[(curr, best_next)],
                                        sat_neighbor_to_if[(best_next, curr)]
                                    )

                            else:
                                # curr is LEO + use_meo: collect candidates (LEO toward handoff or cross-link to best_entry_meo)
                                w_handoff_to_entry = sat_net_graph_only_satellites_with_isls.edges[(best_handoff_leo, best_entry_meo)]["weight"]
                                candidates_b = []
                                for neighbor_id in leo_subgraph.neighbors(curr):
                                    d_n_to_handoff = d_leo(neighbor_id, best_handoff_leo)
                                    if math.isinf(d_n_to_handoff):
                                        continue
                                    score = (
                                        leo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                        + d_n_to_handoff
                                        + w_handoff_to_entry
                                    )
                                    candidates_b.append((score, neighbor_id))

                                for m, w_cross in leo_to_meo_neighbors.get(curr, []):
                                    if m == best_entry_meo:
                                        candidates_b.append((w_cross, m))
                                        break

                                candidates_b = drop_2cycle_candidates(candidates_b, curr, dst_gs_node_id, fstate)
                                best_next = pick_best_tiebreak(candidates_b)
                                if best_next is not None:
                                    pair = if_pair(curr, best_next)
                                    if pair is not None:
                                        out_if, in_if = pair
                                        next_hop_decision = (best_next, out_if, in_if)

                        else:
                            # curr is MEO: 
                            # - if direct link to dst_sat -> go to dst_sat; 
                            # - else best MEO route to a gateway
                            gateway_meo = pick_gateway_from_meo(curr, dst_sat)

                            if gateway_meo is None:
                                next_hop_decision = (-1, -1, -1)
                            else:
                                if sat_net_graph_only_satellites_with_isls.has_edge(curr, dst_sat):
                                    pair = if_pair(curr, dst_sat)
                                    if pair is not None:
                                        out_if, in_if = pair
                                        next_hop_decision = (dst_sat, out_if, in_if)
                                    else:
                                        next_hop_decision = (-1, -1, -1)
                                else:
                                    try:
                                        h_curr = hop_meo[curr][gateway_meo]
                                    except KeyError:
                                        h_curr = None

                                    if h_curr is None:
                                        next_hop_decision = (-1, -1, -1)
                                    else:
                                        candidates = []
                                        for neighbor_id in meo_subgraph.neighbors(curr):
                                            try:
                                                h_nbr = hop_meo[neighbor_id][gateway_meo]
                                            except KeyError:
                                                continue

                                            if h_nbr >= h_curr:
                                                continue

                                            score = (
                                                meo_subgraph.edges[(curr, neighbor_id)]["weight"]
                                                + d_meo(neighbor_id, gateway_meo)
                                            )
                                            candidates.append((score, neighbor_id))

                                        candidates = drop_2cycle_candidates(candidates, curr, dst_gs_node_id, fstate)
                                        best_next = pick_best_tiebreak(candidates)

                                        if best_next is None:
                                            next_hop_decision = (-1, -1, -1)
                                        else:
                                            next_hop_decision = (
                                                best_next,
                                                sat_neighbor_to_if[(curr, best_next)],
                                                sat_neighbor_to_if[(best_next, curr)]
                                            )

                # Save for GS->GS stage
                dist_satellite_to_ground_station[(curr, dst_gs_node_id)] = distance_to_ground_station_m

                # Safety: only dst_sat (LEO) may forward to GS 
                if possibilities:
                    nh = next_hop_decision[0]
                    if nh >= len(satellites) and curr != dst_sat:
                        next_hop_decision = (-1, -1, -1)

                # Write to forwarding state 
                if not prev_fstate or prev_fstate.get((curr, dst_gs_node_id)) != next_hop_decision:
                    f_out.write("%d,%d,%d,%d,%d\n" % (
                        curr,
                        dst_gs_node_id,
                        next_hop_decision[0],
                        next_hop_decision[1],
                        next_hop_decision[2]
                    ))
                fstate[(curr, dst_gs_node_id)] = next_hop_decision

        # ----------------------------
        # GS -> GS
        # ----------------------------
        for src_gid in range(len(ground_stations)):
            for dst_gid in range(len(ground_stations)):
                if src_gid == dst_gid:
                    continue

                src_gs_node_id = len(satellites) + src_gid
                dst_gs_node_id = len(satellites) + dst_gid

                possible_src_sats = []
                for gsl_dist_m, sat_id in ground_station_satellites_in_range[src_gid]:
                    if is_leo(sat_id):
                        possible_src_sats.append((gsl_dist_m, sat_id))

                possibilities = []
                for gsl_dist_m, sat_id in possible_src_sats:
                    best_offered = dist_satellite_to_ground_station.get((sat_id, dst_gs_node_id), float("inf"))
                    if not math.isinf(best_offered):
                        possibilities.append((gsl_dist_m + best_offered, sat_id))
                possibilities.sort()

                next_hop_decision = (-1, -1, -1)
                if possibilities:
                    src_sat_id = pick_best_tiebreak(possibilities)
                    next_hop_decision = (
                        src_sat_id,
                        0,
                        num_isls_per_sat[src_sat_id] + gid_to_sat_gsl_if_idx[src_gid]
                    )

                if not prev_fstate or prev_fstate.get((src_gs_node_id, dst_gs_node_id)) != next_hop_decision:
                    f_out.write("%d,%d,%d,%d,%d\n" % (
                        src_gs_node_id,
                        dst_gs_node_id,
                        next_hop_decision[0],
                        next_hop_decision[1],
                        next_hop_decision[2]
                    ))
                fstate[(src_gs_node_id, dst_gs_node_id)] = next_hop_decision

    if enable_verbose_logs:
        print("")

    return {"fstate": fstate}