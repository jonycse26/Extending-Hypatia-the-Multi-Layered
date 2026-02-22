# Multi-Layer Satellite Constellation Experiments

This directory contains experiments to evaluate the performance of multi-layer satellite constellations (LEO + MEO) implemented in Hypatia.

## Overview

The experiments demonstrate and evaluate:
1. **Multi-layer vs LEO-only comparison** - Shows benefits of MEO backhaul for long-distance traffic
2. **MEO threshold behavior** - Tests when MEO is used based on distance/hop thresholds
3. **Load performance** - Evaluates multi-layer performance under different traffic loads

## Example Files

Three standalone example files are provided for quick demonstration:

- **`example_1_meo_routing.py`** - Proof-of-concept MEO routing demonstration
- **`example_2_comparison.py`** - Multi-layer vs LEO-only performance comparison  
- **`example_3_load_test.py`** - Load performance evaluation under different traffic conditions

See `EXAMPLES.md` for detailed usage instructions for each example.

## Quick Start

### Step 0: Generate Constellation States (First Time Only)
```bash
cd paper/ns3_experiments/multilayer
python step_0_generate_constellation.py
```

This will generate both:
- Multi-layer constellation (LEO + MEO) 
- LEO-only baseline (for comparison)

**Note**: This step can take **2-4 hours** depending on your system:
- Multi-layer constellation: ~2-3 hours (1,192 satellites, complex routing)
- LEO-only baseline: ~30-60 minutes (1,156 satellites, simpler routing)
- Total: **2-4 hours**

**Why it takes so long:**
- Generates dynamic state for 200 seconds with 100ms time steps (2,000 time steps)
- Multi-layer routing algorithm is computationally expensive
- Each time step requires path calculations for all satellite pairs
- Uses 4 threads for parallel processing

**Check progress while running:**
```bash
# In another terminal, check progress:
python check_progress.py

# Or check manually:
ls ../../satellite_networks_state/gen_data/kuiper_630_meo/dynamic_state_ground_stations/fstate_*.txt | wc -l
# Should show ~2000 files when complete
```

**If it's taking too long, you can:**
1. Reduce duration (e.g., 50 seconds instead of 200):
   - Edit `step_0_generate_constellation.py` line 73: `duration_s = 50` 
2. Increase time step (e.g., 200ms instead of 100ms):
   - Edit line 74: `time_step_ms = 200`
3. Use more threads (if you have more CPU cores):
   - Edit line 75: `num_threads = 8`

### Step 1: Generate Run Configurations
```bash
python step_1_generate_runs.py
```
This creates the run directories and configuration files for all experiments.

### Step 2: Run Simulations
```bash
python step_2_run.py
```
This executes all ns-3 simulations. The script runs up to 4 simulations in parallel.

### Step 3: Generate Plots (Optional)
```bash
python step_3_generate_plots.py
```
This generates plots comparing multi-layer vs LEO-only performance.

## Prerequisites

If you prefer to generate constellation states manually:

1. **Generate the multi-layer constellation state:**
   ```bash
   cd ../../satellite_networks_state
   python main_kuiper_630_meo.py 200 100 isls_plus_grid_with_cross_layer ground_stations_top_100 algorithm_free_one_multi_layer 4
   ```

2. **Ensure LEO-only baseline exists** (for comparison):
   ```bash
   python main_kuiper_630.py 200 100 isls_plus_grid ground_stations_top_100 algorithm_free_one_only_over_isls 4
   ```
 
## Running Experiments

The experiments follow a three-step process:

### Step 1: Generate Run Configurations
```bash
python step_1_generate_runs.py
```
This creates the run directories and configuration files for all experiments.

### Step 2: Run Simulations 
```bash
python step_2_run.py
```
This executes all ns-3 simulations. The script runs up to 4 simulations in parallel.

### Step 3: Generate Plots (Optional)
```bash
python step_3_generate_plots.py
```
This generates plots comparing multi-layer vs LEO-only performance.

## Experiment Details

### Experiment 1: Multi-layer vs LEO-only Comparison
- **Purpose**: Demonstrate the benefit of MEO backhaul for long-distance communication
- **Pairs tested** (3 pairs, each with TCP and ping measurements):
  1. **Rio de Janeiro to St. Petersburg** (~11,000 km)
     - Multi-layer: `multilayer_1210_to_1265_*`
     - LEO-only: `leo_only_1174_to_1229_*`
  2. **Manila to Dalian** (~2,800 km)
     - Multi-layer: `multilayer_1209_to_1277_*`
     - LEO-only: `leo_only_1173_to_1241_*`
  3. **Istanbul to Nairobi** (~4,500 km)
     - Multi-layer: `multilayer_1206_to_1288_*`
     - LEO-only: `leo_only_1170_to_1252_*`
- **Metrics**: RTT, throughput, path length, ISL utilization

### Experiment 2: MEO Threshold Behavior
- **Purpose**: Understand when MEO is used based on distance/hop thresholds
- **Pairs tested** (3 pairs with different distances):
  - `threshold_test_1209_to_1277_*` (Manila to Dalian, ~2,800 km)
  - `threshold_test_1210_to_1265_*` (Rio de Janeiro to St. Petersburg, ~11,000 km)
  - `threshold_test_1216_to_1213_*` (Shorter distance)
- **Metrics**: MEO utilization, routing decisions, path characteristics

### Experiment 3: Load Performance
- **Purpose**: Evaluate multi-layer performance under different traffic loads
- **Pairs tested** (3 pairs × 3 load levels = 9 runs):
  - `load_test_*_load_1206_to_1288_tcp` (Istanbul to Nairobi)
  - `load_test_*_load_1210_to_1265_tcp` (Rio de Janeiro to St. Petersburg)
  - `load_test_*_load_1216_to_1213_tcp` (Shorter distance)
- **Load levels**: 5 Mbps (low), 10 Mbps (medium), 20 Mbps (high)
- **Metrics**: Throughput, latency, queue utilization, MEO efficiency

## Expected Results

The multi-layer constellation should show:
- **Reduced latency** for long-distance pairs (via MEO backhaul)
- **Lower LEO ISL utilization** (traffic offloaded to MEO)
- **Better scalability** under high load conditions
- **Improved path efficiency** for distances > 10,000 km or > 3 hops

## Where to Find Results

After running the experiments, results are stored in:

### Main Result Directories:
- **`runs/`** - Individual experiment run directories with logs
- **`data/`** - Extracted and processed data (after step 3)
- **`pdf/`** - Generated plots (after step 3)

### Example Result Paths:



**Experiment 1 (Comparison) - 3 pairs:**

1. **Rio de Janeiro to St. Petersburg** (~11,000 km):
   - Multi-layer TCP: `runs/multilayer_1210_to_1265_tcp/logs_ns3/`
   - LEO-only TCP: `runs/leo_only_1174_to_1229_tcp/logs_ns3/`
   - Multi-layer Pings: `runs/multilayer_1210_to_1265_pings/logs_ns3/`
   - LEO-only Pings: `runs/leo_only_1174_to_1229_pings/logs_ns3/`
   - Plots: `pdf/multilayer_1210_to_1265_tcp/` and `pdf/leo_only_1174_to_1229_tcp/`

2. **Manila to Dalian** (~2,800 km):
   - Multi-layer TCP: `runs/multilayer_1209_to_1277_tcp/logs_ns3/`
   - LEO-only TCP: `runs/leo_only_1173_to_1241_tcp/logs_ns3/`
   - Multi-layer Pings: `runs/multilayer_1209_to_1277_pings/logs_ns3/`
   - LEO-only Pings: `runs/leo_only_1173_to_1241_pings/logs_ns3/`
   - Plots: `pdf/multilayer_1209_to_1277_tcp/` and `pdf/leo_only_1173_to_1241_tcp/`

3. **Istanbul to Nairobi** (~4,500 km):
   - Multi-layer TCP: `runs/multilayer_1206_to_1288_tcp/logs_ns3/`
   - LEO-only TCP: `runs/leo_only_1170_to_1252_tcp/logs_ns3/`
   - Multi-layer Pings: `runs/multilayer_1206_to_1288_pings/logs_ns3/`
   - LEO-only Pings: `runs/leo_only_1170_to_1252_pings/logs_ns3/`
   - Plots: `pdf/multilayer_1206_to_1288_tcp/` and `pdf/leo_only_1170_to_1252_tcp/`

**Experiment 2 (Threshold) - 3 pairs:**
- `runs/threshold_test_1209_to_1277_*/logs_ns3/` (Manila to Dalian)
- `runs/threshold_test_1210_to_1265_*/logs_ns3/` (Rio de Janeiro to St. Petersburg)
- `runs/threshold_test_1216_to_1213_*/logs_ns3/` (Shorter distance)
- ISL utilization: `runs/threshold_test_*/logs_ns3/isl_utilization.csv`
- Plots: `pdf/threshold_test_*/`

**Experiment 3 (Load) - 3 pairs with 3 load levels each:**
- `runs/load_test_low_load_1206_to_1288_tcp/logs_ns3/` (Istanbul to Nairobi, 5 Mbps)
- `runs/load_test_medium_load_1206_to_1288_tcp/logs_ns3/` (Istanbul to Nairobi, 10 Mbps)
- `runs/load_test_high_load_1206_to_1288_tcp/logs_ns3/` (Istanbul to Nairobi, 20 Mbps)
- `runs/load_test_low_load_1210_to_1265_tcp/logs_ns3/` (Rio de Janeiro to St. Petersburg, 5 Mbps)
- `runs/load_test_medium_load_1210_to_1265_tcp/logs_ns3/` (Rio de Janeiro to St. Petersburg, 10 Mbps)
- `runs/load_test_high_load_1210_to_1265_tcp/logs_ns3/` (Rio de Janeiro to St. Petersburg, 20 Mbps)
- `runs/load_test_low_load_1216_to_1213_tcp/logs_ns3/` (Shorter distance, 5 Mbps)
- `runs/load_test_medium_load_1216_to_1213_tcp/logs_ns3/` (Shorter distance, 10 Mbps)
- `runs/load_test_high_load_1216_to_1213_tcp/logs_ns3/` (Shorter distance, 20 Mbps)
- Plots: `pdf/load_test_*_load_*/`

### Key Result Files in Each Run:
- `console.txt` - Simulation console output
- `tcp_flow_0_progress.csv` - TCP flow progress measurements
- `tcp_flow_0_rtt.csv` - TCP RTT measurements
- `tcp_flow_0_cwnd.csv` - TCP congestion window
- `isl_utilization.csv` - ISL utilization data
- `pingmesh.csv` - Ping measurements (for ping runs)

**Note on Node IDs**: Multi-layer constellation has 36 additional MEO satellites, so ground station node IDs are offset by +36 compared to LEO-only. For example:
- LEO-only: Rio de Janeiro = 1174, St. Petersburg = 1229
- Multi-layer: Rio de Janeiro = 1210 (1174+36), St. Petersburg = 1265 (1229+36)

See `QUICK_START.md` for detailed result locations and viewing commands.

## Analysis

After running experiments, analyze:
1. **RTT comparison**: Multi-layer vs LEO-only for each pair
2. **Path analysis**: Number of hops, path length, MEO usage
3. **Utilization**: ISL utilization in LEO vs MEO layers
4. **Throughput**: Goodput under different load conditions

## Coverage Limitations

### Important: Kuiper-630 Coverage Gaps

**The Kuiper-630 constellation used in these experiments has significant coverage limitations:**

- **Constellation size**: 1,156 LEO satellites (34 orbits × 34 satellites per orbit)
- **Kuiper's planned constellation**: ~3,236 satellites
- **Current simulation**: Only **35.7%** of the planned constellation

**Impact on experiments:**
- Ground stations may have **very low path availability** (1-2% or less)
- Some ground station pairs may have **0% path availability**
- This is a **constellation limitation**, not a bug in the routing algorithm
- Both multi-layer and LEO-only scenarios are equally affected

**Why this happens:**
1. The partial constellation (1,156 satellites) doesn't provide continuous global coverage
2. Even with a 3,628 km GSL range (10° elevation), coverage gaps exist
3. Ground station locations may fall in coverage gaps between orbital planes
4. Time-varying satellite positions create intermittent coverage

**Solutions:**
1. **Document the limitation**: Accept that this is a known constraint of using a partial constellation
2. **Use different pairs**: Try shorter-distance pairs that may have better coverage
3. **Use a different constellation**: Consider Starlink-550 (4,408 satellites) for better coverage
4. **Extend constellation**: Modify `main_kuiper_630_meo.py` to use more satellites (requires regeneration)

**Note**: This limitation affects both multi-layer and LEO-only scenarios equally. When paths exist, the multi-layer constellation should show benefits from MEO backhaul, but the low path availability means simulations may have sparse data.

## Notes

- The MEO threshold is currently set to 10,000 km distance or 3 hops
- Ground stations connect only to LEO satellites
- MEO acts as a backhaul to relieve LEO ISL congestion
- All experiments use TCP NewReno for consistency
- **GSL range**: 3,628 km (10° elevation angle) - increased from 1,260 km (30° elevation) to improve coverage

