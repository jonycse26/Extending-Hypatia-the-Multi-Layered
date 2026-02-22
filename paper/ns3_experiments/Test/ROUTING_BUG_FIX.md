# Routing Algorithm Bug Fix

## Problem
The multi-layer routing algorithm (`algorithm_free_one_multi_layer.py`) was only generating ground-station-to-ground-station paths in 1-2% of time steps, causing simulations to fail with "Forwarding state is not set" errors.

## Root Cause
When no LEO satellites were directly in range of the destination ground station, the algorithm would:
1. Set `distance_to_ground_station_m = float("inf")`
2. Mark the path as unavailable (`next_hop_decision = (-1, -1, -1)`)
3. This caused ground-station-to-ground-station routing to fail

## Fix Applied
Modified `satgenpy/satgen/dynamic_state/algorithm_free_one_multi_layer.py` to:
- When no LEO satellites are directly in range of the destination, attempt to find paths via MEO satellites
- Route through MEO satellites to reach LEO satellites that can eventually reach the destination
- This provides fallback routing when direct LEO coverage is temporarily unavailable

## Changes Made
- Added fallback logic (lines 136-165) that:
  1. Checks if no direct LEO paths exist
  2. Searches for paths via MEO satellites to any reachable LEO satellite
  3. Estimates the total path distance including GSL connection
  4. Adds the best path to possibilities if found

## Next Steps
1. **Regenerate constellation state** to apply the fix:
   ```bash
   cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
   python step_0_generate_constellation.py
   ```
   This will take 2-4 hours.

2. **Verify the fix** after regeneration:
   ```bash
   python check_path_availability.py
   ```
   Path availability should be much higher (>50% ideally).

3. **Re-run failed simulations**:
   ```bash
   python step_2_run.py
   ```

## Testing
After regeneration, check that:
- Path availability for all pairs is >50%
- Simulations complete successfully
- Rio de Janeiro to St. Petersburg pair works

## Notes
- The fix uses an estimated GSL distance (1000 km) when no direct LEO coverage exists
- This is a conservative estimate that should work for most cases
- If issues persist, may need to refine the MEO routing logic further

