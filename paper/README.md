# Hypatia paper reproduction

Steps and scripts to reproduce the experiments and figures in *Exploring the
“Internet from space” with Hypatia* (IMC 2020). Use Linux (e.g. Ubuntu 18+).

## Getting the data without running everything

Some steps take hours. Pre-generated artifacts are available:

1. Download `hypatia_paper_temp_data.tar.gz` into this folder (`paper/`):

   https://github.com/snkas/hypatia/releases

   SHA-256 (v1): `18d761a28706723b57772e0636fbc40b7d57161f4c54069eede0c8ae740cbe2d`

2. Install Python packages and gnuplot:
   ```
   pip install numpy
   pip install git+https://github.com/snkas/exputilpy.git@v1.6
   pip install git+https://github.com/snkas/networkload.git@v1.3
   sudo apt-get install gnuplot
   ```

3. Extract:
   ```
   cd paper
   python extract_temp_data.py
   ```

## Getting started (full reproduction)

1. Generate LEO satellite network state over time:

   `paper/satellite_networks_state/README.md`

2. Build the ns-3 simulator:

   `ns3-sat-sim/README.md`

3. Run satgenpy analysis:

   `paper/satgenpy_analysis/README.md`

4. Run ns-3 experiments:

   `paper/ns3_experiments/README.md`

5. Generate satviz figures (paper section in that README):

   `satviz/README.md`

6. Plot paper figures:

   `paper/figures/README.md`
