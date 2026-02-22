# Troubleshooting Guide

## Common Issues

### Issue: "FileNotFoundError: config_ns3.properties does not exist"

**Problem**: The simulation can't find the configuration file.

**Solution**: Run step 1 to generate the run configurations:
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
python step_1_generate_runs.py
```

### Issue: "FileNotFoundError: tcp_flow_0_progress.csv does not exist" (when running step 3)

**Problem**: You're trying to generate plots before running the simulations.

**Solution**: Run the simulations first:
```bash
python step_2_run.py
```

Wait for all simulations to complete (this can take a long time - hours depending on your system).

### Issue: Simulations fail immediately

**Check**:
1. Are the constellation states generated?
   ```bash
   ls ../../satellite_networks_state/gen_data/kuiper_630_meo_*
   ```
   If not, run:
   ```bash
   python step_0_generate_constellation.py
   ```

2. Are the config files created?
   ```bash
   ls runs/multilayer_1174_to_1229_tcp/config_ns3.properties
   ```
   If not, run:
   ```bash
   python step_1_generate_runs.py
   ```

### Issue: "The distance between two satellites exceeded the maximum ISL length"

**Problem**: Cross-layer ISL distance validation failed.

**Solution**: This should be fixed in the latest code. If you still see this:
1. Make sure you have the latest version of the code
2. The fix includes:
   - Reduced number of cross-layer ISLs
   - More lenient distance validation for cross-layer links
   - Increased maximum distance calculation

### Issue: Step 3 fails with "No such file or directory"

**Problem**: The plotting script tries to plot results that don't exist.

**Solution**: The updated step_3 script now checks if files exist before plotting. It will skip missing runs and continue with available ones.

### Issue: "x range is invalid" or "no valid points" error during plotting

**Problem**: Some simulation result files (e.g., `tcp_flow_0_cwnd.csv`) are empty, causing gnuplot to fail.

**Solution**: 
1. This usually means the simulation didn't complete successfully or the flow didn't establish properly
2. Check the simulation console output:
   ```bash
   cat runs/[run_name]/logs_ns3/console.txt
   ```
3. The updated step_3 script now handles this gracefully and will skip runs with empty data files
4. If you see this error, the simulation may need to be re-run

### Issue: "File .../fstate_XXXXX.txt does not exist" during simulation

**Problem**: The dynamic state files are missing or incomplete. This can happen if:
- The constellation state generation was interrupted
- There's a gap in the generated dynamic state files

**Solution**: 
1. Check if dynamic state files exist:
   ```bash
   ls ../../satellite_networks_state/gen_data/kuiper_630_meo_*/dynamic_state_100ms_for_200s/fstate_*.txt | wc -l
   ```
   You should see ~2000 files (one per 100ms for 200 seconds).

2. If files are missing or there are gaps, regenerate the constellation states:
   ```bash
   python step_0_generate_constellation.py
   ```
   This will regenerate all dynamic state files (takes 10-30 minutes).

3. After regeneration, re-run the simulations:
   ```bash
   python step_2_run.py
   ```

### Issue: "AttributeError: _ARRAY_API not found" or "ImportError: numpy.core.multiarray failed to import"

**Problem**: NumPy version incompatibility. The code requires NumPy < 1.25.0, but NumPy 2.x is installed.

**Solution**: Downgrade NumPy to a compatible version:
```bash
pip3 install "numpy<1.25.0" --user
```

Then verify it works:
```bash
python3 -c "import numpy; import scipy; print('OK')"
```

**Note**: If you have NumPy installed system-wide, you may need to use `pip3 install --user` to install a compatible version in your user directory, which will take precedence.

## Correct Order of Operations

1. **Generate constellation states** (first time only, takes 10-30 minutes):
   ```bash
   python step_0_generate_constellation.py
   ```

2. **Generate run configurations**:
   ```bash
   python step_1_generate_runs.py
   ```

3. **Run simulations** (takes hours - runs 27 experiments):
   ```bash
   python step_2_run.py
   ```
   
   **Check progress**:
   ```bash
   screen -ls  # See running simulations
   ls runs/*/logs_ns3/*.csv  # Check for output files
   ```

4. **Generate plots** (after simulations complete):
   ```bash
   python step_3_generate_plots.py
   ```

## Checking Simulation Status

### See if simulations are running:
```bash
screen -ls
```

### Check if a specific simulation completed:
```bash
ls runs/multilayer_1174_to_1229_tcp/logs_ns3/tcp_flow_0_progress.csv
```

### View simulation console output:
```bash
tail -f runs/multilayer_1174_to_1229_tcp/logs_ns3/console.txt
```

### Count completed simulations:
```bash
find runs -name "tcp_flow_0_progress.csv" | wc -l
find runs -name "pingmesh.csv" | wc -l
```

## Expected File Structure

After step 1:
```
runs/
  multilayer_1174_to_1229_tcp/
    config_ns3.properties  ✓
    schedule.csv           ✓
```

After step 2:
```
runs/
  multilayer_1174_to_1229_tcp/
    config_ns3.properties  ✓
    schedule.csv           ✓
    logs_ns3/
      console.txt          ✓
      tcp_flow_0_progress.csv  ✓
      tcp_flow_0.log       ✓
```

After step 3:
```
pdf/
  multilayer_1174_to_1229_tcp/
    *.pdf                  ✓
data/
  multilayer_1174_to_1229_tcp/
    *.csv                  ✓
```

### Issue: Step 0 (Constellation Generation) Taking Too Long

**Problem**: `step_0_generate_constellation.py` is taking 2+ hours instead of the expected 10-30 minutes.

**Why it's slow:**
- Multi-layer constellation has 1,192 satellites (vs 1,156 for LEO-only)
- Multi-layer routing algorithm is computationally more expensive
- Generates 2,000 time steps (200 seconds × 10 steps/second)
- Each time step requires path calculations for all satellite pairs

**Expected time:**
- Multi-layer: **2-3 hours** (normal for complex routing)
- LEO-only: **30-60 minutes** (simpler routing)
- Total: **2-4 hours** is normal

**Check if it's actually working:**
```bash
# Check if process is running:
ps aux | grep main_kuiper

# Check progress (in another terminal):
cd paper/ns3_experiments/multilayer
python check_progress.py

# Or manually count files:
ls ../../satellite_networks_state/gen_data/kuiper_630_meo/dynamic_state_ground_stations/fstate_*.txt 2>/dev/null | wc -l
# Should show ~2000 files when complete
```

**If you need faster generation (for testing):**
1. **Reduce duration** (edit `step_0_generate_constellation.py`):
   ```python
   duration_s = 50  # Instead of 200 (reduces to 500 time steps)
   ```

2. **Increase time step** (less granular):
   ```python
   time_step_ms = 200  # Instead of 100 (reduces to 1000 time steps)
   ```

3. **Use more threads** (if you have more CPU cores):
   ```python
   num_threads = 8  # Instead of 4
   ```

**Note**: Reducing duration/time_step will make simulations less accurate but faster to generate.

