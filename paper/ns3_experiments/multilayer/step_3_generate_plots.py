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

# What this script does (and does NOT)
# ------------------------------------
# Generates gnuplot TCP-flow and pingmesh outputs under pdf/ and data/ for:
#   - Experiments 1–2: get_tcp_run_list() (multilayer / leo_only / threshold_test)
#   - Experiment 3: example3_distance_*_tcp (get_tcp_run_list_for_step3_plots), if logs exist
#
# Experiment 3 TCP runs are created by step_1 like the others; missing/empty logs are skipped.
#
# Still not covered: example1_threshold_* (example_1_threshold_sensitivity.py) — plot manually via
# plot_tcp_flow.py on those run directories.
#
# This script deletes and recreates the entire pdf/ and data/ directories.
# Run from paper/ns3_experiments/multilayer after step_2 (TCP = exp 1–2 + 3; ping = exp 1–2).
# Missing logs (e.g. exp 3 not simulated) are skipped with a warning.

import exputil
import os

try:
    from .run_list import *
except (ImportError, SystemError):
    from run_list import *

try:
    from .evaluation_utils import run_plot_tcp_flow
except (ImportError, SystemError):
    from evaluation_utils import run_plot_tcp_flow

local_shell = exputil.LocalShell()

core_tcp = get_tcp_run_list()
tcp_runs = get_tcp_run_list_for_step3_plots()
ping_runs = get_pings_run_list()
print(
    "step_3_generate_plots: %d TCP (exp 1–2: %d, exp 3: %d) + %d ping runs."
    % (len(tcp_runs), len(core_tcp), len(tcp_runs) - len(core_tcp), len(ping_runs))
)
print("  Exp 3: example3_distance_{short,medium,long}_*_tcp (after step_0 + step_2).")
print("  Not covered: example1_threshold_* — use plot_tcp_flow.py on those run dirs.")
print("  Clearing pdf/ and data/ ...")

# Remove
local_shell.remove_force_recursive("pdf")
local_shell.make_full_dir("pdf")
local_shell.remove_force_recursive("data")
local_shell.make_full_dir("data")

# TCP runs (same plot_tcp_flow invocation as evaluation_utils.run_plot_tcp_flow / example_3)
for run in tcp_runs:
    try:
        run_plot_tcp_flow(run["name"])
    except Exception as e:
        print("ERROR: Failed to generate plots for %s: %s" % (run["name"], str(e)))
        continue

# Ping runs
for run in ping_runs:
    # Check if simulation results exist
    # pingmesh scheduler creates pingmesh.csv (not pingmesh_[from]_[to].log)
    ping_file = "runs/" + run["name"] + "/logs_ns3/pingmesh.csv"
    if not os.path.exists(ping_file):
        print("WARNING: Skipping %s - simulation results not found (run step_2_run.py first)" % run["name"])
        continue
    
    local_shell.make_full_dir("pdf/" + run["name"])
    local_shell.make_full_dir("data/" + run["name"])
    try:
        local_shell.perfect_exec(
            "cd ../../../ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_ping; "
            "python plot_ping.py "
            "../../../../../../../paper/ns3_experiments/multilayer/runs/" + run["name"] + "/logs_ns3 "
            "../../../../../../../paper/ns3_experiments/multilayer/data/" + run["name"] + " "
            "../../../../../../../paper/ns3_experiments/multilayer/pdf/" + run["name"] + " "
            "" + str(run["from_id"]) + " " + str(run["to_id"]) + " " + str(1 * 1000 * 1000 * 1000),  # from -> to
                                                                                                     # 1s interval
            output_redirect=exputil.OutputRedirect.CONSOLE
        )
    except Exception as e:
        print("ERROR: Failed to generate plots for %s: %s" % (run["name"], str(e)))
        continue

print("Success: generated plots")
print("Plots are available in the pdf/ directory")

