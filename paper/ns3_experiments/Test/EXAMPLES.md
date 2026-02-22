# Example Experiments for Multi-Layer Satellite Constellation

This directory contains three standalone example files that demonstrate different aspects of the multi-layer satellite constellation implementation:

## Overview

1. **`example_1_meo_routing.py`** - Proof-of-concept MEO routing demonstration
2. **`example_2_comparison.py`** - Multi-layer vs LEO-only performance comparison
3. **`example_3_load_test.py`** - Load performance evaluation under different traffic conditions

## Example 1: Proof-of-Concept MEO Routing

**File**: `example_1_meo_routing.py`

**Purpose**: Demonstrates that the multi-layer constellation can route traffic via MEO satellites.

**What it shows**:
- Ground stations connect to LEO satellites
- Long-distance traffic (>10,000 km or >3 hops) is routed via MEO backhaul
- MEO satellites act as backhaul to relieve LEO ISL congestion

**Usage**:
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
python example_1_meo_routing.py
```

**What it creates**:
- Run configuration: `runs/example1_meo_routing_1210_to_1265_tcp/`
- Tests: Rio de Janeiro to St. Petersburg (~11,000 km)

**Expected results**:
- Traffic routes via MEO satellites (node IDs 1156-1191)
- Path shows: LEO → MEO → LEO pattern
- MEO ISL utilization > 0

**Verification**:
After running the simulation, check:
- `runs/example1_meo_routing_*/logs_ns3/console.txt` - Routing paths
- `runs/example1_meo_routing_*/logs_ns3/isl_utilization.csv` - MEO ISL usage
- `runs/example1_meo_routing_*/logs_ns3/tcp_flow_0_progress.csv` - Flow progress

---

## Example 2: Multi-Layer vs LEO-Only Comparison

**File**: `example_2_comparison.py`

**Purpose**: Compares the performance of multi-layer (LEO + MEO) vs LEO-only constellations for long-distance communication.

**What it shows**:
- Reduced latency for long-distance pairs via MEO backhaul
- Lower LEO ISL utilization (traffic offloaded to MEO)
- Improved path efficiency for distances > 10,000 km

**Usage**:
```bash
python example_2_comparison.py
```

**What it creates**:
- Multi-layer configurations: `runs/multilayer_*_tcp/`
- LEO-only configurations: `runs/leo_only_*_tcp/`
- Tests multiple pairs:
  - Rio de Janeiro to St. Petersburg (~11,000 km)
  - Manila to Dalian (~2,800 km)

**Expected results**:
- Multi-layer shows lower latency for long-distance pairs
- Multi-layer has lower LEO ISL utilization
- Multi-layer paths include MEO satellites

**Verification**:
Compare results between multi-layer and LEO-only runs:
- RTT: Compare pingmesh results
- Throughput: Compare TCP flow progress
- ISL utilization: Compare LEO ISL usage (should be lower in multi-layer)
- Path length: Check routing paths (multi-layer should use MEO)

---

## Example 3: Load Performance Evaluation

**File**: `example_3_load_test.py`

**Purpose**: Evaluates multi-layer constellation performance under different traffic loads.

**What it shows**:
- Performance under low load (5 Mbps)
- Performance under medium load (10 Mbps)
- Performance under high load (20 Mbps)
- Scalability benefits of multi-layer constellations

**Usage**:
```bash
python example_3_load_test.py
```

**What it creates**:
- `runs/load_test_low_load_*_tcp/` (5 Mbps)
- `runs/load_test_medium_load_*_tcp/` (10 Mbps)
- `runs/load_test_high_load_*_tcp/` (20 Mbps)
- Tests: Rio de Janeiro to St. Petersburg (~11,000 km)

**Expected results**:
- Multi-layer maintains better performance under high load
- MEO backhaul helps distribute load across layers
- Lower queue buildup in LEO ISLs due to MEO offloading
- More consistent latency under varying load conditions

**Verification**:
Compare results across load levels:
- Throughput: Compare TCP flow progress
- Latency: Compare RTT under different loads
- Queue utilization: Check queue sizes in ISL utilization logs
- MEO efficiency: Compare MEO ISL usage across load levels

---

## Running the Examples

### Prerequisites

1. **Generate constellation states** (if not already done):
   ```bash
   python step_0_generate_constellation.py
   ```

2. **Run the example script** to create configurations:
   ```bash
   python example_1_meo_routing.py    # Creates proof-of-concept run
   python example_2_comparison.py     # Creates comparison runs
   python example_3_load_test.py     # Creates load test runs
   ```

### Running Simulations

After creating the configurations, run the simulations:

**Option 1: Run individually**
```bash
cd ../../../ns3-sat-sim/simulator
./waf --run "main_satnet --run_dir=../../paper/ns3_experiments/multilayer/runs/[run_name]"
```

**Option 2: Use the batch runner**
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
python step_2_run.py
```

### Analyzing Results

After simulations complete, you can:

1. **View console output**:
   ```bash
   cat runs/[run_name]/logs_ns3/console.txt
   ```

2. **Check ISL utilization**:
   ```bash
   cat runs/[run_name]/logs_ns3/isl_utilization.csv
   ```

3. **View TCP flow progress**:
   ```bash
   cat runs/[run_name]/logs_ns3/tcp_flow_0_progress.csv
   ```

4. **Generate plots** (if step_3_generate_plots.py is available):
   ```bash
   python step_3_generate_plots.py
   ```

---

## Key Metrics to Evaluate

### Proof-of-Concept (Example 1)
- ✓ MEO satellites are used in routing paths
- ✓ MEO ISL utilization > 0
- ✓ Path includes MEO nodes (1156-1191)

### Comparison (Example 2)
- ✓ Latency reduction in multi-layer vs LEO-only
- ✓ LEO ISL utilization reduction in multi-layer
- ✓ Path efficiency improvement

### Load Performance (Example 3)
- ✓ Throughput maintained under high load
- ✓ Queue utilization stays reasonable
- ✓ MEO helps distribute load

---

## Notes

- All examples use the multi-layer constellation with MEO backhaul
- Ground stations connect only to LEO satellites
- MEO routing is triggered for distances > 10,000 km or paths > 3 hops
- Examples are designed to be standalone and easy to understand
- Each example focuses on a specific aspect of multi-layer performance

