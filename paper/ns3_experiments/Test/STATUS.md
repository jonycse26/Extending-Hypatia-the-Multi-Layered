# Simulation Status

## Current Status

**Last checked**: The plotting script (`step_3_generate_plots.py`) shows that no simulation results are available yet.

## What This Means

The warnings you see indicate that:
- Run configurations have been created (step 1 completed ✓)
- Simulations have NOT been run yet (step 2 pending)
- Plots cannot be generated until simulations complete

## Next Steps

### 1. Run Simulations

Execute the simulations:
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
python step_2_run.py
```

**Note**: This will run 27 experiments and can take several hours depending on your system.

### 2. Monitor Progress

While simulations are running, you can check progress:

```bash
# Count completed simulations
find runs -name "finished.txt" | wc -l

# Check if a specific simulation completed
ls runs/multilayer_1210_to_1265_tcp/logs_ns3/finished.txt

# View console output of a running simulation
tail -f runs/multilayer_1210_to_1265_tcp/logs_ns3/console.txt
```

### 3. Generate Plots (After Simulations Complete)

Once simulations finish:
```bash
python step_3_generate_plots.py
```

## Expected Timeline

- **Step 0** (Generate constellation): 10-30 minutes (one-time)
- **Step 1** (Generate runs): < 1 minute ✓
- **Step 2** (Run simulations): Several hours (27 experiments)
- **Step 3** (Generate plots): 1-5 minutes

## Quick Status Check

Run this to see current status:
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer

echo "=== Run Configurations ==="
ls -d runs/*/ 2>/dev/null | wc -l
echo "run directories created"

echo ""
echo "=== Completed Simulations ==="
find runs -name "finished.txt" 2>/dev/null | wc -l
echo "simulations completed"

echo ""
echo "=== Available Results ==="
find runs -name "tcp_flow_0_progress.csv" 2>/dev/null | wc -l
echo "TCP results available"
find runs -name "pingmesh.csv" 2>/dev/null | wc -l
echo "ping results available"
```

## Troubleshooting

If simulations fail, check:
1. Are constellation states generated? (`step_0_generate_constellation.py`)
2. Are run configurations created? (`step_1_generate_runs.py`)
3. Check console output: `cat runs/[run_name]/logs_ns3/console.txt`

See `TROUBLESHOOTING.md` for more details.

