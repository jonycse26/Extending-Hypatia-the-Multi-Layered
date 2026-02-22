# Example 1 Results - File Locations

## Where to Find PDF and Data Files

For `example_1_meo_routing.py`, the results are stored in the following locations:

### Base Directory
```
/home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer/
```

### Run Name
```
example1_meo_routing_1210_to_1265_tcp
```

---

## Step-by-Step: Getting Your Results

### Step 1: Run the Example Script
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
python example_1_meo_routing.py
```

This creates the run configuration in:
```
runs/example1_meo_routing_1210_to_1265_tcp/
```

### Step 2: Run the Simulation
```bash
cd ../../../ns3-sat-sim/simulator
./waf --run "main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp"
```

After simulation, raw results are in:
```
runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/
├── console.txt
├── tcp_flow_0_progress.csv
├── tcp_flow_0.log
├── isl_utilization.csv
└── finished.txt
```

### Step 3: Generate PDF Plots and Processed Data

After the simulation completes, generate plots:

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow
python plot_tcp_flow.py \
  ../../../../../../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3 \
  ../../../../../../../paper/ns3_experiments/multilayer/data/example1_meo_routing_1210_to_1265_tcp \
  ../../../../../../../paper/ns3_experiments/multilayer/pdf/example1_meo_routing_1210_to_1265_tcp \
  0 1000000000
```

---

## Result File Locations

### PDF Plots
**Location**: `pdf/example1_meo_routing_1210_to_1265_tcp/`

**Files**:
- `plot_tcp_flow_time_vs_progress_0.pdf` - Progress over time
- `plot_tcp_flow_time_vs_rate_0.pdf` - Throughput over time
- `plot_tcp_flow_time_vs_cwnd_0.pdf` - Congestion window over time
- `plot_tcp_flow_time_vs_rtt_0.pdf` - Round-trip time over time

**Full path**:
```
/home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer/pdf/example1_meo_routing_1210_to_1265_tcp/
```

### Processed Data Files
**Location**: `data/example1_meo_routing_1210_to_1265_tcp/`

**Files**:
- `tcp_flow_0_progress.csv` - Processed flow progress
- `tcp_flow_0_rate_in_intervals.csv` - Throughput in 1-second intervals
- `tcp_flow_0_cwnd.csv` - Congestion window size over time
- `tcp_flow_0_rtt.csv` - Round-trip time measurements

**Full path**:
```
/home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer/data/example1_meo_routing_1210_to_1265_tcp/
```

### Raw Simulation Logs
**Location**: `runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/`

**Files**:
- `console.txt` - Full console output
- `tcp_flow_0_progress.csv` - Raw TCP flow progress
- `tcp_flow_0.log` - Detailed TCP flow log
- `isl_utilization.csv` - ISL utilization data (check for MEO usage!)

**Full path**:
```
/home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/
```

---

## Quick Commands

### View PDF plots
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
ls -lh pdf/example1_meo_routing_1210_to_1265_tcp/*.pdf
```

### View processed data
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
ls -lh data/example1_meo_routing_1210_to_1265_tcp/*.csv
```

### Check MEO routing (in ISL utilization)
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
grep -E "115[6-9]|11[6-9][0-9]|119[0-1]" runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/isl_utilization.csv
```
This searches for MEO satellite node IDs (1156-1191) in the ISL utilization file.

### Open a PDF plot
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
xdg-open pdf/example1_meo_routing_1210_to_1265_tcp/plot_tcp_flow_time_vs_progress_0.pdf
```

---

## Summary

| Type | Location | Created After |
|------|----------|---------------|
| **PDF Plots** | `pdf/example1_meo_routing_1210_to_1265_tcp/` | Step 3 (plotting) |
| **Processed Data** | `data/example1_meo_routing_1210_to_1265_tcp/` | Step 3 (plotting) |
| **Raw Logs** | `runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/` | Step 2 (simulation) |

**Note**: PDF and data files are only created after running the plotting script. The raw simulation logs are created immediately after the simulation completes.

