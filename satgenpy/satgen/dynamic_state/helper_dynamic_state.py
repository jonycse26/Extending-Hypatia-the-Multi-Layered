# The MIT License (MIT)
#
# Copyright (c) 2020 ETH Zurich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from satgen.isls import *
from satgen.ground_stations import *
from satgen.tles import *
from satgen.interfaces import *
from .generate_dynamic_state import generate_dynamic_state
import os
import math
from multiprocessing.dummy import Pool as ThreadPool


def worker(args):

    # Extract arguments
    (
        output_dynamic_state_dir,
        epoch,
        simulation_end_time_ns,
        time_step_ns,
        offset_ns,
        satellites,
        ground_stations,
        list_isls,
        list_gsl_interfaces_info,
        max_gsl_length_m,
        max_isl_length_m,
        dynamic_state_algorithm,
        print_logs,
        description_file_path
     ) = args

    # Generate dynamic state
    generate_dynamic_state(
        output_dynamic_state_dir,
        epoch,
        simulation_end_time_ns,
        time_step_ns,
        offset_ns,
        satellites,
        ground_stations,
        list_isls,
        list_gsl_interfaces_info,
        max_gsl_length_m,
        max_isl_length_m,
        dynamic_state_algorithm,  # Options:
                                  # "algorithm_free_one_only_gs_relays"
                                  # "algorithm_free_one_only_over_isls"
                                  # "algorithm_free_gs_one_sat_many_only_over_isls"
                                  # "algorithm_paired_many_only_over_isls"
                                  # "algorithm_free_one_multi_layer"
        print_logs,
        description_file_path
    )


def help_dynamic_state(
        output_generated_data_dir, num_threads, name, time_step_ms, duration_s,
        max_gsl_length_m, max_isl_length_m, dynamic_state_algorithm, print_logs
):

    # Directory
    output_dynamic_state_dir = output_generated_data_dir + "/" + name + "/dynamic_state_" + str(time_step_ms) \
                               + "ms_for_" + str(duration_s) + "s"
    if not os.path.isdir(output_dynamic_state_dir):
        os.makedirs(output_dynamic_state_dir)

    # In nanoseconds
    simulation_end_time_ns = duration_s * 1000 * 1000 * 1000
    time_step_ns = time_step_ms * 1000 * 1000

    # FIX: Include time 0, so we need +1 to the calculation count
    # For duration=5s and time_step=1s, we need: 0, 1, 2, 3, 4, 5 (6 steps, not 5)
    num_calculations = int(math.floor(simulation_end_time_ns / time_step_ns)) + 1
    calculations_per_thread = int(math.floor(float(num_calculations) / float(num_threads)))
    num_threads_with_one_more = num_calculations % num_threads

    # Prepare arguments
    current = 0
    list_args = []
    for i in range(num_threads):

        # How many time steps to calculate for
        num_time_steps = calculations_per_thread
        if i < num_threads_with_one_more:
            num_time_steps += 1

        # Variables (load in for each thread such that they don't interfere)
        ground_stations = read_ground_stations_extended(output_generated_data_dir + "/" + name + "/ground_stations.txt")
        tles = read_tles(output_generated_data_dir + "/" + name + "/tles.txt")
        satellites = tles["satellites"]
        list_isls = read_isls(output_generated_data_dir + "/" + name + "/isls.txt", len(satellites))
        list_gsl_interfaces_info = read_gsl_interfaces_info(
            output_generated_data_dir + "/" + name + "/gsl_interfaces_info.txt",
            len(satellites),
            len(ground_stations)
        )
        epoch = tles["epoch"]

        # Print goal
        print("Thread %d does interval [%.2f ms, %.2f ms]" % (
            i,
            (current * time_step_ns) / 1e6,
            ((current + num_time_steps) * time_step_ns) / 1e6
        ))

        # Description file path (for multi-layer constellations)
        description_file_path = output_generated_data_dir + "/" + name + "/description.txt"
        if not os.path.exists(description_file_path):
            description_file_path = None

        # FIX: Calculate end_time correctly for each thread
        # The range in generate_dynamic_state.py is: range(offset_ns, simulation_end_time_ns + time_step_ns, time_step_ns)
        # So if we want Thread 0 to generate [0s, 1s] (2 steps), we need:
        #   range(0, end_time + time_step_ns, time_step_ns) = [0, 1s]
        #   This means: end_time + time_step_ns = 2s, so end_time = 1s
        # But we're calculating: end_time = (current + num_time_steps) * time_step_ns = 2s
        # So we need to subtract time_step_ns to account for the +time_step_ns in the range
        if i == num_threads - 1:  # Last thread
            # For the last thread, ensure we include the final time step (duration_s)
            # The range adds time_step_ns, so we pass duration_s (not duration_s - time_step_ns)
            # Then range(offset, duration_s + time_step_ns, time_step_ns) will include duration_s
            end_time = simulation_end_time_ns
        else:
            # For non-last threads, subtract time_step_ns to account for the +time_step_ns in the range
            end_time = (current + num_time_steps) * time_step_ns - time_step_ns
        
        list_args.append((
            output_dynamic_state_dir,
            epoch,
            end_time,
            time_step_ns,
            current * time_step_ns,
            satellites,
            ground_stations,
            list_isls,
            list_gsl_interfaces_info,
            max_gsl_length_m,
            max_isl_length_m,
            dynamic_state_algorithm,
            print_logs,
            description_file_path
        ))

        current += num_time_steps

    # Run in parallel
    pool = ThreadPool(num_threads)
    pool.map(worker, list_args)
    pool.close()
    pool.join()
