# this is the algorithm for the free one multi-layer satellite constellation

from .fstate_calculation import *
import math


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
        leo_num_sats,  # Number of LEO satellites (MEO satellites start after this)
        meo_threshold_distance_m=10000000.0,  # 10,000 km threshold
        meo_threshold_hops=3  # 3 hop threshold
):
    """
    FREE-ONE MULTI-LAYER ALGORITHM

    "one"
    This algorithm assumes that every satellite and ground station has exactly 1 GSL interface.

    "free"
    This 1 interface is bound to a maximum outgoing bandwidth, but can send to any other
    GSL interface (well, satellite -> ground-station, and ground-station -> satellite) in
    range. ("free") There is no reciprocation of the bandwidth asserted.

    "multi_layer"
    Ground stations connect only to LEO satellites. LEO satellites can forward traffic
    via MEO satellites when:
    - The distance to destination is > meo_threshold_distance_m (default: 10,000 km), OR
    - The number of hops required is > meo_threshold_hops (default: 3)

    MEO satellites act as a backhaul to relieve the ISLs of the LEO shell.

    """

    if enable_verbose_logs:
        print("\nALGORITHM: FREE ONE MULTI-LAYER")
        print("  > LEO satellites: 0 to %d" % (leo_num_sats - 1))
        print("  > MEO satellites: %d to %d" % (leo_num_sats, len(satellites) - 1))
        print("  > MEO threshold distance: %.2f km" % (meo_threshold_distance_m / 1000.0))
        print("  > MEO threshold hops: %d" % meo_threshold_hops)

    # Check the graph
    if sat_net_graph_only_satellites_with_isls.number_of_nodes() != len(satellites):
        raise ValueError("Number of nodes in the graph does not match the number of satellites")
    for sid in range(len(satellites)):
        for n in sat_net_graph_only_satellites_with_isls.neighbors(sid):
            if n >= len(satellites):
                raise ValueError("Graph cannot contain satellite-to-ground-station links")

    #################################
    # BANDWIDTH STATE
    #

    # There is only one GSL interface for each node (pre-condition), which as-such will get the entire bandwidth
    output_filename = output_dynamic_state_dir + "/gsl_if_bandwidth_" + str(time_since_epoch_ns) + ".txt"
                  # node_id , number_of_ISL_interfaces , max_GSL_bandwidth
    if enable_verbose_logs:
        print("  > Writing interface bandwidth state to: " + output_filename)
    with open(output_filename, "w+") as f_out:
        if time_since_epoch_ns == 0:
            for node_id in range(len(satellites)):
                f_out.write("%d,%d,%f\n"
                            % (node_id, num_isls_per_sat[node_id],
                               list_gsl_interfaces_info[node_id]["aggregate_max_bandwidth"]))
            for node_id in range(len(satellites), len(satellites) + len(ground_stations)):
                f_out.write("%d,%d,%f\n"
                            % (node_id, 0, list_gsl_interfaces_info[node_id]["aggregate_max_bandwidth"]))

    #################################
    # FORWARDING STATE
    #

    # Previous forwarding state (to only write delta)
    prev_fstate = None
    if prev_output is not None:
        prev_fstate = prev_output["fstate"]

    # GID to satellite GSL interface index
    gid_to_sat_gsl_if_idx = [0] * len(ground_stations)  # (Only one GSL interface per satellite, so the first)
             #In your model: one GSL interface per satellite, so the index is always 0.
                #Why it exists (even if always 0)
                #Because the general Hypatia design supports cases like: multiple GSL interfaces per satellite,
                # different ground stations bound to different satellite GSL interfaces

    # Calculate the shortest paths for the entire satellite network (LEO + MEO)
    if enable_verbose_logs:
        print("  > Calculating Floyd-Warshall for multi-layer graph")
    import networkx as nx
    dist_sat_net_without_gs = nx.floyd_warshall_numpy(sat_net_graph_only_satellites_with_isls)
            #dist_sat_net_without_gs[i, j] = shortest-path distance from satellite i to satellite j

    # Forwarding state
    fstate = {}
            # key: (src_node_id, dst_node_id)
            # value: (next_hop_node_id, out_if, in_if)

    # Now write state to file for complete graph
    output_filename = output_dynamic_state_dir + "/fstate_" + str(time_since_epoch_ns) + ".txt"
    if enable_verbose_logs:
        print("  > Writing forwarding state to: " + output_filename)
    with open(output_filename, "w+") as f_out:
            # fstate_<time>.txt

        # Satellites to ground stations
        # From the satellites attached to the destination ground station,
        # select the one which promises the shortest path to the destination ground station
        dist_satellite_to_ground_station = {}
        for curr in range(len(satellites)):
            for dst_gid in range(len(ground_stations)):
                dst_gs_node_id = len(satellites) + dst_gid

                # Among the satellites in range of the destination ground station,
                # find the one which promises the shortest distance
                # Note: Only LEO satellites can connect to ground stations
                possible_dst_sats = []
                for b in ground_station_satellites_in_range[dst_gid]:
                    if b[1] < leo_num_sats:  # Only LEO satellites ; b[0] is GSL distance, b[1] is satellite id
                        possible_dst_sats.append(b)

                possibilities = []
                for b in possible_dst_sats:
                    if not math.isinf(dist_sat_net_without_gs[(curr, b[1])]):  # Must be reachable
                        # Calculate path distance
                        path_distance = dist_sat_net_without_gs[(curr, b[1])] + b[0]
                            #total distance to GS=ISL path dist(curr→dst_sat)+ GSL dist(dst_sat→GS)
                        # Count hops (approximate by dividing distance by average ISL length)
                        # For simplicity, we'll use a different approach: check if we need MEO
                        # by looking at the distance
                        possibilities.append(
                            (
                                path_distance,
                                b[1],
                                path_distance  # Store distance for threshold check
                            )
                        )
                possibilities = list(sorted(possibilities))

                # By default, if there is no satellite in range for the
                # destination ground station, it will be dropped (indicated by -1)
                next_hop_decision = (-1, -1, -1)
                    # no next hop → packet will be dropped (invalid route)
                distance_to_ground_station_m = float("inf")
                        # we treat this GS as unreachable from curr unless we find a valid option.
                if len(possibilities) > 0:
                    dst_sat = possibilities[0][1]
                    distance_to_ground_station_m = possibilities[0][0]
                        # dist(curr→dst_sat via ISLs)+dist(dst_sat→GS via GSL)

                    # Determine if we should use MEO as backhaul
                    use_meo = False   #✅ do NOT use MEO
                    if curr < leo_num_sats:  # Current node is LEO
                        # Check if distance threshold is exceeded
                        if distance_to_ground_station_m > meo_threshold_distance_m:
                            #If the best LEO-based route to reach the destination GS is “too long” (e.g., > 10,000 km),
                                #then switch to MEO backhaul.
                                # for example
                                #distance_to_ground_station_m = 12,000,000 → use_meo=True immediately.
                            use_meo = True
                        # Check if hop threshold would be exceeded (approximate)
                        # We'll check this by looking at the path length
                        elif not math.isinf(dist_sat_net_without_gs[(curr, dst_sat)]):
                            # Estimate hops (rough approximation)
                            avg_isl_length = 2000000.0  # ~2000 km average ISL
                            estimated_hops = int(dist_sat_net_without_gs[(curr, dst_sat)] / avg_isl_length) + 1
                            if estimated_hops > meo_threshold_hops:
                                    # for example
                                    # distance_to_ground_station_m = 8,000,000
                                    # but dist(curr, dst_sat)=7,000,000
                                    # estimated_hops = int(7,000,000 / 2,000,000) + 1 = int(3.5)+1 = 3+1 = 4
                                    # 4 > 3 ⇒ use_meo=True
                                use_meo = True

                    # If the current node is not that satellite, determine how to get to the satellite
                        #curr = current satellite node (could be LEO or MEO)
                    if curr != dst_sat:
                        if use_meo and curr < leo_num_sats:
                            # Route via MEO: find nearest MEO satellite
                            best_meo_sat = None
                            best_distance_to_meo = float("inf")
                                # dist(curr→meo_sat)+dist(meo_sat→dst_sat)
                            for meo_sat in range(leo_num_sats, len(satellites)):
                                if not math.isinf(dist_sat_net_without_gs[(curr, meo_sat)]):
                                    # Check if this MEO satellite can reach destination
                                    if not math.isinf(dist_sat_net_without_gs[(meo_sat, dst_sat)]):
                                        # LEO(curr) → … → MEO(meo_sat) → … → LEO(dst_sat)
                                        total_via_meo = (
                                                dist_sat_net_without_gs[(curr, meo_sat)] +
                                                dist_sat_net_without_gs[(meo_sat, dst_sat)]
                                        )
                                            # total_via_meo=dist(curr,meo_sat)+dist(meo_sat,dst_sat)
                                        if total_via_meo < best_distance_to_meo:
                                            best_distance_to_meo = total_via_meo
                                            best_meo_sat = meo_sat
                                                # curr→best_meo_sat→dst_sat

                            if best_meo_sat is not None:
                                # Route to MEO satellite first
                                best_distance_m = 1000000000000000
                                    # This is basically “infinity” in meters.
                                    # We will try every neighbor and minimize this value.
                                for neighbor_id in sat_net_graph_only_satellites_with_isls.neighbors(curr):
                                        # dist_sat_net_without_gs[(neighbor_id, best_meo_sat)] is finite.
                                        # EO–LEO,
                                        # LEO–MEO (cross-layer),
                                        # or if curr were MEO, MEO–MEO too — but here curr is LEO)
                                    distance_m = (
                                            sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                            +
                                            dist_sat_net_without_gs[(neighbor_id, best_meo_sat)]
                                                # cost(curr→neighbor)+shortest_dist(neighbor→best_meo_sat)
                                    )
                                    if distance_m < best_distance_m:
                                            # If this neighbor gives a better (smaller) total cost, update decision.
                                        next_hop_decision = (
                                            neighbor_id, # next_hop = neighbor_id
                                            sat_neighbor_to_if[(curr, neighbor_id)],
                                                #out_if = sat_neighbor_to_if[(curr, neighbor_id)]
                                            sat_neighbor_to_if[(neighbor_id, curr)]
                                                # in_if = sat_neighbor_to_if[(neighbor_id, curr)]
                                        )
                                        best_distance_m = distance_m
                            else:
                                # Fall back to direct LEO routing
                                best_distance_m = 1000000000000000
                                    # We will test every neighbor and pick the smallest cost.
                                for neighbor_id in sat_net_graph_only_satellites_with_isls.neighbors(curr):
                                    distance_m = (
                                            sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                            +
                                            dist_sat_net_without_gs[(neighbor_id, dst_sat)]
                                                # score=w(curr,neighbor)+shortestDist(neighbor→dst_sat)
                                    )
                                    if distance_m < best_distance_m:
                                        next_hop_decision = (
                                            neighbor_id,
                                                # next_hop = neighbor_id (send packet there next)
                                            sat_neighbor_to_if[(curr, neighbor_id)],
                                                # next_hop = neighbor_id (send packet there next)
                                            sat_neighbor_to_if[(neighbor_id, curr)]
                                                # out_if = interface on curr used to reach neighbor_id
                                        )
                                        best_distance_m = distance_m
                        else:
                            # Direct routing (LEO only or MEO routing)
                            best_distance_m = 1000000000000000
                            for neighbor_id in sat_net_graph_only_satellites_with_isls.neighbors(curr):
                                distance_m = (
                                        sat_net_graph_only_satellites_with_isls.edges[(curr, neighbor_id)]["weight"]
                                        +
                                        dist_sat_net_without_gs[(neighbor_id, dst_sat)]
                                )
                                if distance_m < best_distance_m:
                                    next_hop_decision = (
                                        neighbor_id,
                                        sat_neighbor_to_if[(curr, neighbor_id)],
                                        sat_neighbor_to_if[(neighbor_id, curr)]
                                    )
                                    best_distance_m = distance_m
                    else:
                        # This is the destination satellite, as such the next hop is the ground station itself
                        next_hop_decision = (
                            dst_gs_node_id,
                            num_isls_per_sat[dst_sat] + gid_to_sat_gsl_if_idx[dst_gid],
                            0
                        )

                # In any case, save the distance of the satellite to the ground station to re-use
                dist_satellite_to_ground_station[(curr, dst_gs_node_id)] = distance_to_ground_station_m

                # Write to forwarding state
                if not prev_fstate or prev_fstate.get((curr, dst_gs_node_id)) != next_hop_decision:
                        # If there is no previous forwarding state (prev_fstate is None)
                        # If there is no previous forwarding state (prev_fstate is None)
                    f_out.write("%d,%d,%d,%d,%d\n" % (
                        curr,
                        dst_gs_node_id,
                        next_hop_decision[0],
                        next_hop_decision[1],
                        next_hop_decision[2]
                    ))
                fstate[(curr, dst_gs_node_id)] = next_hop_decision

        # Ground stations to ground stations
        # Choose the source satellite which promises the shortest path
        for src_gid in range(len(ground_stations)):
            for dst_gid in range(len(ground_stations)):
                if src_gid != dst_gid:
                    src_gs_node_id = len(satellites) + src_gid
                    dst_gs_node_id = len(satellites) + dst_gid

                    # Among the satellites in range of the source ground station,
                    # find the one which promises the shortest distance
                    # Note: Only LEO satellites can connect to ground stations
                        # a[0] = distance from source GS to that satellite (GSL distance)
                        # a[1] = satellite ID
                    possible_src_sats = []
                    for a in ground_station_satellites_in_range[src_gid]:
                        if a[1] < leo_num_sats:  # Only LEO satellites
                                # GS → Satellite links only go to LEO satellites.
                            possible_src_sats.append(a)

                    possibilities = []
                    for a in possible_src_sats:
                        best_distance_offered_m = dist_satellite_to_ground_station.get((a[1], dst_gs_node_id),
                                                                                       float("inf"))
                        if not math.isinf(best_distance_offered_m):
                            possibilities.append(
                                (
                                    a[0] + best_distance_offered_m,
                                    a[1]
                                )
                            )
                    possibilities = sorted(possibilities)

                    # By default, if there is no satellite in range for one of the
                    # ground stations, it will be dropped (indicated by -1)
                    next_hop_decision = (-1, -1, -1)
                    if len(possibilities) > 0:
                        src_sat_id = possibilities[0][1]
                        next_hop_decision = (
                            src_sat_id,
                            0,
                            num_isls_per_sat[src_sat_id] + gid_to_sat_gsl_if_idx[src_gid]
                        )

                    # Update forwarding state
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

    return {
        "fstate": fstate
    }

