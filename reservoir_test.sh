#!/bin/bash

# Run the graph generation
python graph_generation.py

cd keymaera

# Generate KeymaeraX code
python generate_overflow_model.py --graph ../data/graph.csv --config <TODO> --property safety --output ./reservoir.kyx

# Run KeymaeraX
keymaerax -launch -prove ./reservoir.kyx -tool z3 -timeout 60 -out ./reservoir.kyp