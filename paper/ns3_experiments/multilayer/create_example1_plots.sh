#!/bin/bash
# Script to generate PDF plots and data files for example 1

# Navigate to the plotting directory
cd /home/jonz/ns-allinone-3.35/ns-3.35/hypatia/ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_tcp_flow

# Run the plotting script
python plot_tcp_flow.py \
  ../../../../../../../paper/ns3_experiments/multilayer/runs/example1_meo_routing_1210_to_1265_tcp/logs_ns3 \
  ../../../../../../../paper/ns3_experiments/multilayer/data/example1_meo_routing_1210_to_1265_tcp \
  ../../../../../../../paper/ns3_experiments/multilayer/pdf/example1_meo_routing_1210_to_1265_tcp \
  0 1000000000

echo ""
echo "Done! Files created in:"
echo "  - PDF: paper/ns3_experiments/multilayer/pdf/example1_meo_routing_1210_to_1265_tcp/"
echo "  - Data: paper/ns3_experiments/multilayer/data/example1_meo_routing_1210_to_1265_tcp/"

