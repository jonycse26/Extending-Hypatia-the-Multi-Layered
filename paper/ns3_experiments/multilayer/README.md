# Multi-Layer Satellite Constellation Experiments

This directory contains experiments to evaluate the performance of multi-layer satellite constellations (LEO + MEO) implemented in Hypatia.

## Overview

The experiments demonstrate and evaluate:
1. **Multi-layer vs LEO-only comparison** - Shows benefits of MEO backhaul for long-distance traffic
2. **MEO / routing scenarios (experiment 2)** - Three multilayer flows with **distance-tier labels** (Tokyo–BA, Mumbai–Lima, Lima–Karachi) on default fstate; for **hop/distance threshold sweeps** use `example_1_threshold_sensitivity.py`
3. **Distance-based scenario analysis (Example 3)** - Short / medium / long great-circle pairs (Manila–Dalian, Istanbul–Nairobi, Rio–St. Petersburg) on default multilayer fstate

## Shared evaluation helpers

- **`evaluation_utils.py`** — `extract_metrics`, `export_results_csv`, `run_ns3`, and MEO ISL proxy metrics (used by the example scripts and CSV export).

## Example Files

Three standalone example files are provided for quick demonstration:

- **`example_1_threshold_sensitivity.py`** — **Threshold sensitivity** — uses `experiment1_pairs_multilayer`; sweeps `meo_threshold_hops` (and optional `meo_threshold_distance_m`); regenerates `dynamic_state_*_mh*_md*` per point. *Not* part of step_1–3.
- **`example_2_comparison.py`** — Recreates **experiment 1**-style multilayer vs LEO-only runs (same pairs as `run_list.experiment1_pairs_*`). Optional; step 1 already generates those runs.
- **`example_3_distance_based_scenario_analysis.py`** — **Example 3: Distance-based scenario analysis** — three multilayer TCP runs (`short` / `medium` / `long` great-circle tiers: Manila–Dalian, Istanbul–Nairobi, Rio–St. Petersburg); default `dynamic_state_500ms_for_50s` (same as the step pipeline). Optional `--export-csv-from-runs` for `example_3_distance_scenario_results.csv`.

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

**Note**: `step_0_generate_constellation.py` uses **50 s** duration and **500 ms** timesteps (aligned with `run_list.py` → `dynamic_state_500ms_for_50s`). Runtime depends strongly on CPU and may be significantly longer than the 5s/1000ms setup.

**Why it takes time:** multi-layer routing over 1,192 nodes (LEO + MEO) per snapshot; LEO-only has 1,156 satellites. Default **4** threads.

**Check progress:**
```bash
python check_progress.py
# Snapshot count (multilayer gen_data folder name matches run_list.multilayer_satellite_network):
ls ../../satellite_networks_state/gen_data/kuiper_630_meo_isls_plus_grid_with_cross_layer_ground_stations_top_100_algorithm_free_one_multi_layer/dynamic_state_500ms_for_50s/fstate_*.txt 2>/dev/null | wc -l
```

**Tuning:** edit `duration_s`, `time_step_ms`, `num_threads` in `step_0_generate_constellation.py` (`main()`). If you change duration/timestep, update **`run_list.py`** (and regenerate) so `[DYNAMIC-STATE]` in run configs matches the folder name.

### Step 1: Generate Run Configurations
```bash
python step_1_generate_runs.py
```
Creates run directories for **TCP: experiments 1–2 + 3** and **ping: experiments 1–2** only.

- **Experiment 1** (same idea as `example_2_comparison.py`): paired **multilayer** vs **LEO-only** TCP + ping for **Mumbai–Lima, Lima–Karachi, Tokyo–Buenos-Aires** (`run_list.experiment1_pairs_*`). Compare `pdf/multilayer_*` vs `pdf/leo_only_*`.
- **Experiment 2**: `threshold_test_*` TCP + ping for **Tokyo–BA, Mumbai–Lima, Lima–Karachi** (`experiment2_pairs_multilayer` — distance-tier labels).
- **Experiment 3**: `example3_distance_{short,medium,long}_*_tcp` — **multilayer only**; **Manila–Dalian, Istanbul–Nairobi, Rio–St. Petersburg** (`experiment3_pairs_multilayer`).

`step_1`, `step_2`, and `step_3` all use **`get_tcp_run_list_for_step3_plots()`** for TCP (core experiments 1–2 + experiment 3). Ping runs remain experiments 1–2 only.

All of the above use default **`dynamic_state_500ms_for_50s`** (complete **step 0** first).

### Step 2: Run Simulations
```bash
python step_2_run.py
```
Runs ns-3 for every TCP run from step 1 (including experiment 3), plus all ping runs. Up to 4 simulations in parallel.

### Step 3: Generate Plots (Optional)
```bash
python step_3_generate_plots.py
```
Rebuilds `pdf/` and `data/` with gnuplot outputs for the same TCP runs (exp 1–2 + 3) and ping runs (exp 1–2). Any TCP run with missing or empty logs is skipped with a warning.

**Standalone scripts** (`example_1_threshold_sensitivity.py`, etc.) are separate from this pipeline; their runs are not created by step 1.

## Prerequisites

If you prefer to generate constellation states manually:

1. **Generate the multi-layer constellation state** (arguments must match `run_list.py` / `step_0` — here **50 s**, **500 ms** timestep):
   ```bash
   cd ../../satellite_networks_state
   python main_kuiper_630_meo.py 50 500 isls_plus_grid_with_cross_layer ground_stations_top_100 algorithm_free_one_multi_layer 4
   ```

2. **LEO-only baseline** (same duration / timestep):
   ```bash
   python main_kuiper_630.py 50 500 isls_plus_grid ground_stations_top_100 algorithm_free_one_only_over_isls 4
   ```
 
## Running Experiments

After **step 0**, run **step 1 → 2 → 3** as in [Quick Start](#quick-start). Step 1 **deletes and recreates** `runs/`, `pdf/`, and `data/` — back up anything you need first.

## Experiment Details

### Experiment 1: Multi-layer vs LEO-only Comparison
- **Purpose**: Demonstrate the benefit of MEO backhaul vs LEO-only for the same ground pairs (`run_list.experiment1_pairs_*`).
- **Pairs tested** (3 pairs; TCP + ping each; multilayer node id = LEO id + 36):
  1. **Mumbai to Lima** — multilayer `1196 → 1221`, LEO `1160 → 1185`
  2. **Lima to Karachi** — multilayer `1221 → 1203`, LEO `1185 → 1167`
  3. **Tokyo to Buenos-Aires** — multilayer `1192 → 1204`, LEO `1156 → 1168`
- **Run name pattern**: `multilayer_<from>_to_<to>_{tcp,pings}`, `leo_only_<from>_to_<to>_{tcp,pings}`
- **Metrics**: RTT, throughput, ISL utilization (compare multilayer vs LEO-only plots side by side)

### Experiment 2: MEO Threshold Behavior
- **Purpose**: Same multilayer constellation with **distance-tier labels** (very long / long / shorter) — `run_list.experiment2_pairs_multilayer`.
- **Pairs tested** (TCP + ping; all multilayer):
  - `threshold_test_1192_to_1204_*` — Tokyo to Buenos-Aires (very long)
  - `threshold_test_1196_to_1221_*` — Mumbai to Lima (long)
  - `threshold_test_1221_to_1203_*` — Lima to Karachi (shorter)
- **Metrics**: MEO utilization, routing, path characteristics

### Experiment 3: Distance-based scenario analysis
- **Purpose**: Compare TCP performance and MEO usage across **short / medium / long** great-circle routes on the same multilayer topology (default forwarding state).
- **Pairs tested** (3 TCP runs; README-aligned with experiment 2 style):
  - `example3_distance_short_1209_to_1277_tcp` — Manila to Dalian (~2,800 km)
  - `example3_distance_medium_1206_to_1288_tcp` — Istanbul to Nairobi (~4,500 km)
  - `example3_distance_long_1210_to_1265_tcp` — Rio de Janeiro to St. Petersburg (~11,000 km)
- **Routing**: Default `dynamic_state_500ms_for_50s` (no per-run `meo_threshold_distance_m` sweep).
- **Traffic**: Fixed 10 Mbps per run
- **Metrics**: Throughput, RTT, completion, MEO ISL utilization proxies (`evaluation_utils`)

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

**Experiment 1 (multilayer vs LEO-only) — 3 pairs**

| Pair | Multilayer TCP | LEO-only TCP |
|------|----------------|--------------|
| Mumbai–Lima | `runs/multilayer_1196_to_1221_tcp/` | `runs/leo_only_1160_to_1185_tcp/` |
| Lima–Karachi | `runs/multilayer_1221_to_1203_tcp/` | `runs/leo_only_1185_to_1167_tcp/` |
| Tokyo–Buenos-Aires | `runs/multilayer_1192_to_1204_tcp/` | `runs/leo_only_1156_to_1168_tcp/` |

Same node IDs with `_pings` instead of `_tcp` for pingmesh runs. Plots mirror under `pdf/<run_name>/`.

**Experiment 2 (threshold_test, multilayer only)**

- `runs/threshold_test_1192_to_1204_{tcp,pings}/` — Tokyo–Buenos-Aires  
- `runs/threshold_test_1196_to_1221_{tcp,pings}/` — Mumbai–Lima  
- `runs/threshold_test_1221_to_1203_{tcp,pings}/` — Lima–Karachi  

ISL utilization: `runs/threshold_test_*/logs_ns3/isl_utilization.csv` — Plots: `pdf/threshold_test_*/`

**Experiment 3 (distance tiers) - 3 TCP runs (10 Mbps each):**
- `runs/example3_distance_short_1209_to_1277_tcp/logs_ns3/` (Manila–Dalian)
- `runs/example3_distance_medium_1206_to_1288_tcp/logs_ns3/` (Istanbul–Nairobi)
- `runs/example3_distance_long_1210_to_1265_tcp/logs_ns3/` (Rio–St. Petersburg)
- Plots: `pdf/example3_distance_*_tcp/` after `step_3_generate_plots.py` (or `plot_tcp_flow.py` manually)

### Key Result Files in Each Run:
- `console.txt` - Simulation console output
- `tcp_flow_0_progress.csv` - TCP flow progress measurements
- `tcp_flow_0_rtt.csv` - TCP RTT measurements
- `tcp_flow_0_cwnd.csv` - TCP congestion window
- `isl_utilization.csv` - ISL utilization data
- `pingmesh.csv` - Ping measurements (for ping runs)

**Note on Node IDs**: Multilayer adds **36** MEO satellites before ground stations in the numbering, so **multilayer GS id = LEO-only GS id + 36** (`run_list.OFFSET_DIFF`). Example: **Mumbai** LEO `1160` → multilayer `1196`. Experiment 3 long-haul pair (Rio–St. Petersburg) uses LEO `1174`→`1229` and multilayer `1210`→`1265`.

See `QUICK_START.md` for detailed result locations and viewing commands.

## Analysis

After running experiments, analyze:
1. **RTT comparison**: Multilayer vs LEO-only (experiment 1) for each pair
2. **Path / routing**: Hops, MEO usage (`console.txt`, ISL logs)
3. **Utilization**: LEO vs MEO-touching ISL utilization
4. **Throughput vs distance tier**: Experiment 3 (`example3_distance_{short,medium,long}_*`) on multilayer; experiment 1 for **LEO vs multilayer** goodput on the Mumbai / Lima / Tokyo pairs

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

