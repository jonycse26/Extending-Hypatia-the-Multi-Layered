#!/usr/bin/env python3
"""
Regenerate only the dynamic state (fstate_*.txt, gsl_if_bandwidth_*.txt, coverage CSVs)
for the multi-layer constellation. Uses the existing constellation (TLEs, ISLs, ground
stations, description.txt). Reads max_gsl_length_m and max_isl_length_m from
description.txt so fstate matches current GSL (e.g. 5°).

Run from paper/ns3_experiments/multilayer/:
    python3 regenerate_dynamic_state_only.py [num_threads]
Default num_threads=4. Duration and time step come from run_list.py.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# satellite_networks_state is paper/satellite_networks_state
SATELLITE_NETWORKS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../../satellite_networks_state'))
sys.path.insert(0, SATELLITE_NETWORKS_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../../satgenpy')))

import run_list
from satgen.description import read_description
import satgen


def main():
    output_generated_data_dir = os.path.join(SATELLITE_NETWORKS_DIR, 'gen_data')
    name = run_list.multilayer_satellite_network
    duration_s = run_list.simulation_end_time_s
    time_step_ms = run_list.dynamic_state_update_interval_ms
    dynamic_state_algorithm = "algorithm_free_one_multi_layer"

    constellation_dir = os.path.join(output_generated_data_dir, name)
    description_path = os.path.join(constellation_dir, 'description.txt')

    if not os.path.isdir(constellation_dir):
        print("ERROR: Constellation directory not found: %s" % constellation_dir)
        print("Run step_0_generate_constellation.py first to create the constellation.")
        return 1
    if not os.path.isfile(description_path):
        print("ERROR: description.txt not found: %s" % description_path)
        return 1

    description = read_description(description_path)
    max_gsl_length_m = description.get('max_gsl_length_m')
    max_isl_length_m = description.get('max_isl_length_m')
    if max_gsl_length_m is None or max_isl_length_m is None:
        print("ERROR: description.txt must contain max_gsl_length_m and max_isl_length_m")
        return 1

    num_threads = 4
    if len(sys.argv) > 1:
        try:
            num_threads = int(sys.argv[1])
        except ValueError:
            pass

    dynamic_state_dir = os.path.join(constellation_dir, "dynamic_state_%dms_for_%ds" % (time_step_ms, duration_s))
    if os.path.isdir(dynamic_state_dir):
        import shutil
        print("Removing existing dynamic state dir: %s" % dynamic_state_dir)
        shutil.rmtree(dynamic_state_dir)

    print("Regenerating dynamic state only")
    print("  Constellation: %s" % name)
    print("  Dir: %s" % constellation_dir)
    print("  Duration: %d s, time step: %d ms" % (duration_s, time_step_ms))
    print("  max_gsl_length_m from description: %.0f m" % max_gsl_length_m)
    print("  num_threads: %d" % num_threads)
    print("")

    # Run from satellite_networks_state so paths match main_kuiper_630_meo (gen_data/...)
    os.chdir(SATELLITE_NETWORKS_DIR)
    satgen.help_dynamic_state(
        "gen_data",
        num_threads,
        name,
        time_step_ms,
        duration_s,
        max_gsl_length_m,
        max_isl_length_m,
        dynamic_state_algorithm,
        True,
    )

    print("")
    print("Done. fstate and coverage files updated in:")
    print("  %s" % dynamic_state_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
