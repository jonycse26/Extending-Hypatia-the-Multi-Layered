# Quick Start Guide - Multi-Layer Experiments

## Commands to Run (In Order)

### 1. Navigate to Experiment Directory
```bash
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/paper/ns3_experiments/multilayer
```

### 2. Generate Constellation States (First Time Only - Takes 10-30 minutes)
```bash
python step_0_generate_constellation.py
```

### 3. Generate Run Configurations
```bash
python step_1_generate_runs.py
```

### 4. Run All Simulations (Takes time - runs 27 experiments)
```bash
python step_2_run.py
```

### 5. Generate Plots (After simulations complete)
```bash
python step_3_generate_plots.py
```

---

## Where to Find Results

### Experiment Results Location

All results are stored in: `paper/ns3_experiments/multilayer/`

### Directory Structure After Running:

```
multilayer/
├── runs/                          # Individual experiment runs
│   ├── multilayer_1174_to_1229_tcp/      # Experiment 1: Multi-layer TCP
│   ├── leo_only_1174_to_1229_tcp/        # Experiment 1: LEO-only TCP (comparison)
│   ├── multilayer_1174_to_1229_pings/    # Experiment 1: Multi-layer pings
│   ├── leo_only_1174_to_1229_pings/      # Experiment 1: LEO-only pings
│   ├── threshold_test_1174_to_1229_tcp/  # Experiment 2: Threshold test
│   ├── load_test_low_load_1174_to_1229_tcp/  # Experiment 3: Load test
│   └── ... (27 total runs)
│
├── data/                          # Extracted data from simulations
│   ├── multilayer_1174_to_1229_tcp/
│   ├── leo_only_1174_to_1229_tcp/
│   └── ... (one folder per run)
│
└── pdf/                           # Generated plots
    ├── multilayer_1174_to_1229_tcp/
    ├── leo_only_1174_to_1229_tcp/
    └── ... (one folder per run)
```

### Key Result Files

#### For Each Run (e.g., `runs/multilayer_1174_to_1229_tcp/`):

1. **Simulation Logs**: `runs/[run_name]/logs_ns3/`
   - `console.txt` - Console output
   - `tcp_flow_[id].log` - TCP flow logs
   - `isl_utilization.csv` - ISL utilization data
   - `pingmesh.csv` - Ping measurements (contains all ping pairs)

2. **Extracted Data**: `data/[run_name]/`
   - CSV files with processed metrics
   - Time series data

3. **Plots**: `pdf/[run_name]/`
   - PDF plots showing:
     - Throughput over time
     - RTT over time
     - Queue utilization
     - Path characteristics

---

## Viewing Results by Experiment

### Experiment 1: Multi-layer vs LEO-only Comparison

**Results Location:**
- Multi-layer: `runs/multilayer_*_tcp/` and `runs/multilayer_*_pings/`
- LEO-only: `runs/leo_only_*_tcp/` and `runs/leo_only_*_pings/`

**Key Comparisons:**
- Compare RTT: `pdf/multilayer_1174_to_1229_pings/` vs `pdf/leo_only_1174_to_1229_pings/`
- Compare Throughput: `pdf/multilayer_1174_to_1229_tcp/` vs `pdf/leo_only_1174_to_1229_tcp/`

**Pairs Tested:**
- 1174 → 1229 (Rio de Janeiro to St. Petersburg)
- 1173 → 1241 (Manila to Dalian)
- 1170 → 1252 (Istanbul to Nairobi)

### Experiment 2: MEO Threshold Behavior

**Results Location:**
- `runs/threshold_test_*_tcp/`
- `runs/threshold_test_*_pings/`

**What to Look For:**
- Check ISL utilization logs to see MEO usage
- Compare path lengths in different distance scenarios
- Files: `runs/threshold_test_*/logs_ns3/isl_utilization.csv`

### Experiment 3: Load Performance

**Results Location:**
- `runs/load_test_low_load_*_tcp/` (5 Mbps)
- `runs/load_test_medium_load_*_tcp/` (10 Mbps)
- `runs/load_test_high_load_*_tcp/` (20 Mbps)

**What to Compare:**
- Throughput under different loads
- Queue utilization
- MEO efficiency at different load levels

---

## Quick Commands to View Results

### List All Experiment Runs
```bash
ls -la runs/
```

### View a Specific Run's Logs
```bash
cat runs/multilayer_1174_to_1229_tcp/logs_ns3/console.txt
```

### View ISL Utilization Data
```bash
cat runs/multilayer_1174_to_1229_tcp/logs_ns3/isl_utilization.csv
```

### Open Generated Plots
```bash
# View PDF plots (if you have a PDF viewer)
evince pdf/multilayer_1174_to_1229_tcp/*.pdf
# or
xdg-open pdf/multilayer_1174_to_1229_tcp/
```

### Compare Two Runs Side-by-Side
```bash
# Compare RTT plots
diff data/multilayer_1174_to_1229_pings/ data/leo_only_1174_to_1229_pings/
```

---

## Summary of All 27 Experiments

### Experiment 1: Comparison (12 runs)
- `multilayer_1174_to_1229_tcp` / `leo_only_1174_to_1229_tcp`
- `multilayer_1174_to_1229_pings` / `leo_only_1174_to_1229_pings`
- `multilayer_1173_to_1241_tcp` / `leo_only_1173_to_1241_tcp`
- `multilayer_1173_to_1241_pings` / `leo_only_1173_to_1241_pings`
- `multilayer_1170_to_1252_tcp` / `leo_only_1170_to_1252_tcp`
- `multilayer_1170_to_1252_pings` / `leo_only_1170_to_1252_pings`

### Experiment 2: Threshold (6 runs)
- `threshold_test_1174_to_1229_tcp` / `threshold_test_1174_to_1229_pings`
- `threshold_test_1173_to_1241_tcp` / `threshold_test_1173_to_1241_pings`
- `threshold_test_1180_to_1177_tcp` / `threshold_test_1180_to_1177_pings`

### Experiment 3: Load (9 runs)
- `load_test_low_load_1174_to_1229_tcp`
- `load_test_medium_load_1174_to_1229_tcp`
- `load_test_high_load_1174_to_1229_tcp`
- `load_test_low_load_1170_to_1252_tcp`
- `load_test_medium_load_1170_to_1252_tcp`
- `load_test_high_load_1170_to_1252_tcp`
- `load_test_low_load_1180_to_1177_tcp`
- `load_test_medium_load_1180_to_1177_tcp`
- `load_test_high_load_1180_to_1177_tcp`

---

## Tips

1. **Check if simulations are still running:**
   ```bash
   screen -ls
   ```

2. **Monitor a running simulation:**
   ```bash
   tail -f runs/[run_name]/logs_ns3/console.txt
   ```

3. **Check simulation progress:**
   ```bash
   ls -lh runs/*/logs_ns3/*.log | wc -l
   ```

4. **If simulations fail, check:**
   ```bash
   cat runs/[run_name]/logs_ns3/console.txt | grep -i error
   ```

