# How to View Example 1 Results

This guide shows you exactly which commands to run to see the results from `example_1_meo_routing.py`.

## Step 0: Ensure Constellation States Are Generated

**IMPORTANT**: Before running simulations, make sure constellation states are generated:

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# Check if constellation states exist
ls ../../satellite_networks_state/gen_data/kuiper_630_meo_*/dynamic_state_100ms_for_200s/fstate_*.txt | wc -l
```

**You should see ~2000 files**. If you see fewer or get errors about missing files, regenerate:

```bash
python step_0_generate_constellation.py
```

This takes 10-30 minutes but is required before running simulations.

## Step 1: Check if Simulation Has Run

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# Check if simulation completed
ls runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/finished.txt
```

**If the file exists**: Simulation is complete, go to Step 3.

**If the file doesn't exist**: You need to run the simulation first (Step 2).

---

## Step 2: Run the Simulation (If Not Done Yet)

**Prerequisite**: Make sure Step 0 is completed (constellation states generated).

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/ns3-sat-sim/simulator
./waf --run "main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp"
```

**Note**: This can take 10-30 minutes depending on your system.

**If you see error**: `File .../fstate_XXXXX.txt does not exist`
- This means constellation states need to be regenerated
- Go back to Step 0 and run `python step_0_generate_constellation.py`

**Check progress**:
```bash
tail -f ../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/console.txt
```

---

## Step 3: Generate PDF Plots and Data Files

After the simulation completes, generate the plots:

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow
python plot_tcp_flow.py \
  ../../../../../../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3 \
  ../../../../../../../paper/ns3_experiments/multilayer/data/example1_meo_routing_1210_to_1265_tcp \
  ../../../../../../../paper/ns3_experiments/multilayer/pdf/example1_meo_routing_1210_to_1265_tcp \
  0 1000000000
```

**Or use the helper script**:
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
./create_example1_plots.sh
```

---
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow
python plot_tcp_flow.py \
  ../../../../../../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3 \
  ../../../../../../../paper/ns3_experiments/multilayer/data/example1_meo_routing_1210_to_1265_tcp \
  ../../../../../../../paper/ns3_experiments/multilayer/pdf/example1_meo_routing_1210_to_1265_tcp \
  0 1000000000
## Step 4: View the Results

### View Raw Simulation Logs

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# Console output (routing information)
cat runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/console.txt

# ISL utilization (check for MEO usage - node IDs 1156-1191)
cat runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/isl_utilization.csv

# TCP flow progress
cat runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/tcp_flow_0_progress.csv
```

### View Processed Data Files

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# List all data files
ls -lh data/example1_meo_routing_1210_to_1265_tcp/

# View specific files
cat data/example1_meo_routing_1210_to_1265_tcp/tcp_flow_0_progress.csv
cat data/example1_meo_routing_1210_to_1265_tcp/tcp_flow_0_rate_in_intervals.csv
cat data/example1_meo_routing_1210_to_1265_tcp/tcp_flow_0_cwnd.csv
cat data/example1_meo_routing_1210_to_1265_tcp/tcp_flow_0_rtt.csv
```

### View PDF Plots

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# List all PDF files
ls -lh pdf/example1_meo_routing_1210_to_1265_tcp/*.pdf

# Open a specific plot
xdg-open pdf/example1_meo_routing_1210_to_1265_tcp/plot_tcp_flow_time_vs_progress_0.pdf
xdg-open pdf/example1_meo_routing_1210_to_1265_tcp/plot_tcp_flow_time_vs_rate_0.pdf
xdg-open pdf/example1_meo_routing_1210_to_1265_tcp/plot_tcp_flow_time_vs_cwnd_0.pdf
xdg-open pdf/example1_meo_routing_1210_to_1265_tcp/plot_tcp_flow_time_vs_rtt_0.pdf
```

### Check MEO Routing (Key Verification)

```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# Search for MEO satellite node IDs (1156-1191) in ISL utilization
grep -E "115[6-9]|11[6-9][0-9]|119[0-1]" runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/isl_utilization.csv

# Count MEO ISL links used
grep -E "115[6-9]|11[6-9][0-9]|119[0-1]" runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/isl_utilization.csv | wc -l
```

---

## Quick Command Summary

**All-in-one check**:
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

# Check simulation status
if [ -f "runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/finished.txt" ]; then
    echo "✓ Simulation completed"
    echo ""
    echo "Raw logs:"
    ls -lh runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/*.csv
    echo ""
    echo "Data files:"
    ls -lh data/example1_meo_routing_1210_to_1265_tcp/*.csv 2>/dev/null || echo "  (Run plotting script first)"
    echo ""
    echo "PDF plots:"
    ls -lh pdf/example1_meo_routing_1210_to_1265_tcp/*.pdf 2>/dev/null || echo "  (Run plotting script first)"
else
    echo "✗ Simulation not run yet"
    echo "Run: cd ../../../ns3-sat-sim/simulator && ./waf --run \"main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp\""
fi
```

---

## Expected Results

After running all steps, you should see:

### Raw Logs (in `runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3/`):
- `console.txt` - Full simulation output
- `tcp_flow_0_progress.csv` - TCP flow progress
- `isl_utilization.csv` - ISL usage (should show MEO links)
- `finished.txt` - Completion marker

### Processed Data (in `data/example1_meo_routing_1210_to_1265_tcp/`):
- `tcp_flow_0_progress.csv` - Processed progress
- `tcp_flow_0_rate_in_intervals.csv` - Throughput over time
- `tcp_flow_0_cwnd.csv` - Congestion window
- `tcp_flow_0_rtt.csv` - Round-trip time

### PDF Plots (in `pdf/example1_meo_routing_1210_to_1265_tcp/`):
- `plot_tcp_flow_time_vs_progress_0.pdf` - Progress over time
- `plot_tcp_flow_time_vs_rate_0.pdf` - Throughput over time
- `plot_tcp_flow_time_vs_cwnd_0.pdf` - Congestion window over time
- `plot_tcp_flow_time_vs_rtt_0.pdf` - RTT over time

### Key Verification:
- MEO satellites (node IDs 1156-1191) appear in `isl_utilization.csv`
- MEO ISL utilization > 0
- Routing paths show LEO → MEO → LEO pattern

