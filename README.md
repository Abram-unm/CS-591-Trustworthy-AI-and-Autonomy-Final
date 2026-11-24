# CS-591-Trustworthy-AI-and-Autonomy-Final

The repository for the UNM CS 591 final project in the Fall 2026 semester. By Felix Oteng Mensah, Jocelyn Dailey, and Abram Iverson.

## Purpose

This repository holds code for generating random weighted graphs to combine with constraints to create a KeymaeraX format test to determine if nodes do not surpass a certain value as a barrier function certificate.  
The intent is to model pipe-reservoir systems between 3-10 reservoirs where each graph node represents a reservoir in the system and each edge between nodes represents a pipe connecting two reservoirs.

## Install

### Option 1

1. Clone this repository.  

### Option 2

1. Download this repository as a .zip.
2. Unzip file.

## Requirements

- matplotlib 3.11.2
- networkx 3.7

### Optional

- KeymaeraX 5.1.2 (requires Wolfram Engine)
  - Scripts in this repository assume KeYmaeraX is on your path as `keymaerax`. One way of achieving on this (on Linux) is to put `exec java -jar /path/to/keymaerax.jar "$@"` into `$HOME/.local/bin/keymaerax`, mark it as executable with `chmod +x`, and refresh $PATH.
- Wolfram Engine

## How to run

1. Clone repository to a system with Python.
2. install package requirements listed in ```requirements.txt```.
3. Run from the command line, optionally specifying a node count and output name:
   ```python graph_generation.py --node-count 5 --output-name example```
   The output name is used as the filename stem for `data/example.csv`,
   `data/example.png`, and `keymaera/example.kyx`. If omitted, the node count
   is chosen randomly from 3 to 10 and the output name defaults to `graph`.

### Optional steps

4. Run KeymaeraX.
5. Import the generated file from ```working_directory/keymaera/<output-name>.kyx```
   (or `graph.kyx` when using the default output name).
6. Run test in KeymaeraX.

To run graph generation, model generation, and the KeymaeraX proof from one
command, use:

```bash
bash reservoir_test.sh 3 generated_graph overflow_config.example proof
```

The arguments are node count, graph filename stem, configuration filename stem
under `data/`, and output filename stem under `keymaera/`. Choose a configuration
whose nodes and edges are compatible with the generated graph.

Proofs can also be executed from the command line with `keymaerax -prove keymaera/<input_file>.kyx -tool z3 -timeout 60 -out keymaera/<output_file>.kyp`

## Examples

- `./keymaera/overflow_safety.kyx` contains a minimal three-reservoir problem with no minimum-level requirement, and no saturating flow in channels. The switching policy (from `./data/overflow_config.example.json`) is trivial, with all channels open at all times.
- `./keymaera/overflow_saturated_minimum.kyx` is a slightly more sophisticated example, with minimum levels to be maintained in each reservoir and saturating flows through each channel. It should take less than one minute to prove that the feedback switching policy (from `./data/overflow_config.saturated_minimum.example.json`) is safe.

Proof traces for each problem are provided in the corresponding `./keymaera/*.kyp` file.
