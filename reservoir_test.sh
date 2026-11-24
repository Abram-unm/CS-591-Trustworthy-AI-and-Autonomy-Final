#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: bash reservoir_test.sh NODE_COUNT GRAPH_NAME CONFIG_NAME OUTPUT_NAME" >&2
    echo "  CONFIG_NAME is the filename stem of data/CONFIG_NAME.json, which must exist." >&2
}

if [[ $# -ne 4 ]]; then
    usage
    exit 2
fi

node_count=$1
graph_name=$2
config_name=$3
output_name=$4

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

# Generate the graph CSV, image, and KeymaeraX graph model.
python graph_generation.py --node-count "$node_count" --output-name "$graph_name"

cd "$script_dir/keymaera"

# Generate the configured safety model.
python generate_overflow_model.py \
    --graph "../data/${graph_name}.csv" \
    --config "../data/${config_name}.json" \
    --property safety \
    --output "./${output_name}.kyx"

# Run KeymaeraX.
keymaerax -prove "./${output_name}.kyx" -tool z3 -timeout 60 -out "./${output_name}.kyp"
