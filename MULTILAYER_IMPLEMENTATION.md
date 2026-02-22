# Multi-Layer Satellite Constellation Implementation

## Overview

This document describes the implementation of multi-layer satellite constellation support (LEO + MEO) in Hypatia, including the proof-of-concept routing algorithm and experimental evaluation framework.

## Implementation Components

### 1. Multi-Layer Constellation Generation

**Files:**
- `paper/satellite_networks_state/main_helper_multilayer.py` - Main helper class for generating multi-layer constellations
- `paper/satellite_networks_state/main_kuiper_630_meo.py` - Example multi-layer constellation configuration

**Features:**
- Supports separate LEO and MEO shells with independent orbital parameters
- Generates TLEs for both layers and merges them correctly
- Calculates appropriate GSL and ISL ranges for each layer
- Handles cross-layer ISL generation

### 2. Cross-Layer ISL Generation

**Files:**
- `satgenpy/satgen/isls/generate_multilayer_isls.py` - Multi-layer ISL generation

**Features:**
- Generates ISLs within LEO shell (plus grid pattern)
- Generates ISLs within MEO shell (plus grid pattern)
- Creates cross-layer ISLs connecting LEO to MEO satellites
- Configurable maximum cross-layer ISL distance

### 3. Multi-Layer Routing Algorithm

**Files:**
- `satgenpy/satgen/dynamic_state/algorithm_free_one_multi_layer.py` - Multi-layer routing algorithm

**Algorithm Description:**
- **Ground stations** connect only to LEO satellites
- **MEO as backhaul**: Traffic is routed via MEO when:
  - Distance to destination > 10,000 km, OR
  - Estimated hops > 3
- Uses shortest path routing with MEO preference for long distances
- Automatically detects LEO/MEO split from description file or satellite mean motion

**Key Parameters:**
- `meo_threshold_distance_m`: 10,000,000 m (10,000 km)
- `meo_threshold_hops`: 3 hops

### 4. Description File Extensions

**Files:**
- `satgenpy/satgen/description/generate_description.py` - Extended to store LEO/MEO split
- `satgenpy/satgen/description/read_description.py` - Reader for description metadata

**Features:**
- Stores `leo_num_sats` in description file for multi-layer constellations
- Routing algorithm automatically reads this information

### 5. Experimental Evaluation Framework

**Location:** `paper/ns3_experiments/multilayer/`

**Experiments:**

#### Experiment 1: Multi-layer vs LEO-only Comparison
- **Purpose**: Demonstrate benefits of MEO backhaul for long-distance traffic
- **Pairs**: Rio de Janeiro-St. Petersburg, Manila-Dalian, Istanbul-Nairobi
- **Metrics**: RTT, throughput, path length, ISL utilization
- **Runs**: 12 total (6 TCP + 6 ping, each with multi-layer and LEO-only)

#### Experiment 2: MEO Threshold Behavior
- **Purpose**: Understand when MEO is used based on distance/hop thresholds
- **Pairs**: Different distance scenarios (very long, medium, shorter)
- **Metrics**: MEO utilization, routing decisions, path characteristics
- **Runs**: 6 total (3 TCP + 3 ping)

#### Experiment 3: Load Performance
- **Purpose**: Evaluate multi-layer performance under different traffic loads
- **Load levels**: 5 Mbps, 10 Mbps, 20 Mbps
- **Metrics**: Throughput, latency, queue utilization, MEO efficiency
- **Runs**: 9 total (3 pairs × 3 load levels)

**Total Experiments**: 27 runs (15 TCP + 12 ping)

## Usage

### Generating Constellation State

```bash
cd paper/satellite_networks_state
python main_kuiper_630_meo.py 200 100 isls_plus_grid_with_cross_layer ground_stations_top_100 algorithm_free_one_multi_layer 4
```

### Running Experiments

```bash
cd paper/ns3_experiments/multilayer
python step_0_generate_constellation.py  # First time only
python step_1_generate_runs.py
python step_2_run.py
python step_3_generate_plots.py
```

## Architecture

### Satellite ID Assignment
- LEO satellites: IDs 0 to (LEO_NUM_SATS - 1)
- MEO satellites: IDs LEO_NUM_SATS to (TOTAL_NUM_SATS - 1)

### Routing Logic
1. Ground stations always connect to LEO satellites
2. For traffic from LEO to LEO:
   - If distance > threshold OR hops > threshold: Route via MEO
   - Otherwise: Route directly via LEO ISLs
3. MEO satellites route among themselves and back to LEO as needed

### ISL Structure
- **LEO-LEO**: Plus grid pattern within LEO shell
- **MEO-MEO**: Plus grid pattern within MEO shell
- **LEO-MEO**: Cross-layer links based on orbit position mapping

## Configuration

### Example Multi-Layer Constellation (Kuiper 630 + MEO)

**LEO Shell:**
- Altitude: 630 km
- Orbits: 34
- Satellites per orbit: 34
- Total LEO satellites: 1,156

**MEO Shell:**
- Altitude: 10,000 km
- Orbits: 6
- Satellites per orbit: 6
- Total MEO satellites: 36

**Total**: 1,192 satellites

## Expected Results

The multi-layer constellation should demonstrate:

1. **Reduced Latency**: For long-distance pairs (>10,000 km), MEO backhaul provides shorter paths
2. **Lower LEO ISL Utilization**: Traffic offloaded to MEO reduces congestion in LEO layer
3. **Better Scalability**: MEO handles long-distance traffic, allowing LEO to focus on local/regional traffic
4. **Improved Path Efficiency**: Fewer hops for very long distances via MEO

## Future Work

As mentioned in the thesis requirements, potential extensions include:

1. **Different Routing Implementations**: Compare various routing strategies
2. **Optimization Options**: 
   - Dynamic threshold adjustment
   - Load-aware routing
   - Multi-path routing
3. **Trace-Driven Emulation**: Integrate with workflow for real-world traffic patterns
4. **Additional Metrics**: 
   - Energy consumption
   - Handover frequency
   - Path stability

## Files Modified/Created

### New Files
- `paper/satellite_networks_state/main_helper_multilayer.py`
- `paper/satellite_networks_state/main_kuiper_630_meo.py`
- `satgenpy/satgen/isls/generate_multilayer_isls.py`
- `satgenpy/satgen/dynamic_state/algorithm_free_one_multi_layer.py`
- `satgenpy/satgen/description/read_description.py`
- `paper/ns3_experiments/multilayer/*` (experiment framework)

### Modified Files
- `satgenpy/satgen/isls/__init__.py` - Added multilayer ISL export
- `satgenpy/satgen/description/generate_description.py` - Added LEO/MEO metadata
- `satgenpy/satgen/description/__init__.py` - Added description reader
- `satgenpy/satgen/dynamic_state/generate_dynamic_state.py` - Added multi-layer algorithm support
- `satgenpy/satgen/dynamic_state/helper_dynamic_state.py` - Pass description file path
- `satgenpy/satgen/tles/__init__.py` - Export checksum function

## Testing

The implementation has been tested for:
- ✅ Correct TLE generation and merging
- ✅ ISL generation (intra-layer and cross-layer)
- ✅ Routing algorithm logic
- ✅ Description file metadata
- ✅ Experiment framework setup

## Notes

- The current implementation uses a simple distance/hop-based threshold for MEO usage
- Cross-layer ISL generation uses a regular pattern; more sophisticated approaches could be implemented
- Ground stations connect only to LEO; MEO-only ground station connections could be added
- The routing algorithm is a proof-of-concept; more advanced routing strategies can be implemented

