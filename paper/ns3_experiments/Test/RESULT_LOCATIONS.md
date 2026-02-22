# Example Result File Locations

This document provides the exact file locations for results from the three example experiments.

## Base Directory

All results are located in:
```
/home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer/
```

Or relative path:
```
paper/ns3_experiments/multilayer/
```

---

## Example 1: Proof-of-Concept MEO Routing

### Run Directory
```
runs/example1_meo_routing_1210_to_1265_tcp/
```

### Simulation Results (after running simulation)
```
runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/
├── console.txt                    # Console output with routing information
├── tcp_flow_0_progress.csv        # TCP flow progress over time
├── tcp_flow_0.log                 # Detailed TCP flow log
├── isl_utilization.csv            # ISL utilization data (check for MEO usage)
└── finished.txt                   # Completion marker
```

### Processed Data (after running step_3_generate_plots.py)
```
data/example1_meo_routing_1210_to_1265_tcp/
├── tcp_flow_0_progress.csv        # Processed flow progress
├── tcp_flow_0_rate_in_intervals.csv
├── tcp_flow_0_cwnd.csv            # Congestion window data
└── tcp_flow_0_rtt.csv             # Round-trip time data
```

### Plots (after running step_3_generate_plots.py)
```
pdf/example1_meo_routing_1210_to_1265_tcp/
├── plot_tcp_flow_time_vs_progress_0.pdf
├── plot_tcp_flow_time_vs_rate_0.pdf
├── plot_tcp_flow_time_vs_cwnd_0.pdf
└── plot_tcp_flow_time_vs_rtt_0.pdf
```

### Key Files to Check
- **MEO routing verification**: `runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/isl_utilization.csv`
  - Look for ISL links involving MEO satellites (node IDs 1156-1191)
- **Routing paths**: `runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/console.txt`
  - Search for routing decisions and path information

---

## Example 2: Multi-Layer vs LEO-Only Comparison

### Run Directories

**Multi-layer runs:**
```
runs/multilayer_1210_to_1265_tcp/      # Rio de Janeiro to St. Petersburg
runs/multilayer_1209_to_1277_tcp/     # Manila to Dalian
```

**LEO-only runs:**
```
runs/leo_only_1174_to_1229_tcp/       # Rio de Janeiro to St. Petersburg
runs/leo_only_1173_to_1241_tcp/       # Manila to Dalian
```

### Simulation Results (after running simulation)

For each run (e.g., `multilayer_1210_to_1265_tcp`):
```
runs/multilayer_1210_to_1265_tcp/logs_ns3/
├── console.txt
├── tcp_flow_0_progress.csv
├── tcp_flow_0.log
├── isl_utilization.csv
└── finished.txt
```

### Processed Data (after running step_3_generate_plots.py)
```
data/multilayer_1210_to_1265_tcp/     # Multi-layer data
data/leo_only_1174_to_1229_tcp/       # LEO-only data (for comparison)
```

### Plots (after running step_3_generate_plots.py)
```
pdf/multilayer_1210_to_1265_tcp/      # Multi-layer plots
pdf/leo_only_1174_to_1229_tcp/        # LEO-only plots (for comparison)
```

### Comparison Files

**Compare these files side-by-side:**
- `runs/multilayer_1210_to_1265_tcp/logs_ns3/tcp_flow_0_progress.csv` vs
  `runs/leo_only_1174_to_1229_tcp/logs_ns3/tcp_flow_0_progress.csv`
- `runs/multilayer_1210_to_1265_tcp/logs_ns3/isl_utilization.csv` vs
  `runs/leo_only_1174_to_1229_tcp/logs_ns3/isl_utilization.csv`

---

## Example 3: Load Performance Evaluation

### Run Directories
```
runs/load_test_low_load_1210_to_1265_tcp/      # 5 Mbps
runs/load_test_medium_load_1210_to_1265_tcp/   # 10 Mbps
runs/load_test_high_load_1210_to_1265_tcp/     # 20 Mbps
```

### Simulation Results (after running simulation)

For each load level (e.g., `load_test_low_load_1210_to_1265_tcp`):
```
runs/load_test_low_load_1210_to_1265_tcp/logs_ns3/
├── console.txt
├── tcp_flow_0_progress.csv
├── tcp_flow_0.log
├── isl_utilization.csv
└── finished.txt
```

### Processed Data (after running step_3_generate_plots.py)
```
data/load_test_low_load_1210_to_1265_tcp/
data/load_test_medium_load_1210_to_1265_tcp/
data/load_test_high_load_1210_to_1265_tcp/
```

### Plots (after running step_3_generate_plots.py)
```
pdf/load_test_low_load_1210_to_1265_tcp/
pdf/load_test_medium_load_1210_to_1265_tcp/
pdf/load_test_high_load_1210_to_1265_tcp/
```

### Comparison Files

**Compare across load levels:**
- `runs/load_test_low_load_1210_to_1265_tcp/logs_ns3/tcp_flow_0_progress.csv`
- `runs/load_test_medium_load_1210_to_1265_tcp/logs_ns3/tcp_flow_0_progress.csv`
- `runs/load_test_high_load_1210_to_1265_tcp/logs_ns3/tcp_flow_0_progress.csv`

---

## Quick Reference: File Types

### Raw Simulation Logs
Located in: `runs/[run_name]/logs_ns3/`

- **`console.txt`** - Full console output, routing decisions, errors
- **`tcp_flow_0_progress.csv`** - TCP flow progress (bytes sent over time)
- **`tcp_flow_0.log`** - Detailed TCP flow log
- **`isl_utilization.csv`** - ISL link utilization data
- **`pingmesh.csv`** - Ping measurements (for ping runs)
- **`finished.txt`** - Completion marker (empty file)

### Processed Data
Located in: `data/[run_name]/`

- **`tcp_flow_0_progress.csv`** - Processed flow progress
- **`tcp_flow_0_rate_in_intervals.csv`** - Throughput in time intervals
- **`tcp_flow_0_cwnd.csv`** - Congestion window size
- **`tcp_flow_0_rtt.csv`** - Round-trip time measurements

### Plots
Located in: `pdf/[run_name]/`

- **`plot_tcp_flow_time_vs_progress_0.pdf`** - Progress over time
- **`plot_tcp_flow_time_vs_rate_0.pdf`** - Throughput over time
- **`plot_tcp_flow_time_vs_cwnd_0.pdf`** - Congestion window over time
- **`plot_tcp_flow_time_vs_rtt_0.pdf`** - RTT over time

---

## Quick Commands

### List all example runs
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
ls -d runs/example* runs/load_test_*_1210_to_1265*
```

### Check if simulation completed
```bash
ls runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/finished.txt
```

### View console output
```bash
cat runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/console.txt
```

### View ISL utilization
```bash
cat runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/isl_utilization.csv
```

### View TCP flow progress
```bash
cat runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/tcp_flow_0_progress.csv
```

### Count completed simulations
```bash
find runs -name "finished.txt" | wc -l
```

---

## Notes

- Results are created **after** running simulations (step 2)
- Processed data and plots are created **after** running step 3
- If a file doesn't exist, the simulation may not have completed yet
- Check `console.txt` for any errors or warnings
- MEO satellites have node IDs 1156-1191 (check `isl_utilization.csv` for MEO usage)

