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
- KeymaeraX 5.1.2

## How to run
1. Clone repository to a system with Python.
2. install package requirements listed in ```requirements.txt```.
3. Run from the command line ```python graph_generation.py```
### Optional
4. Run KeymaeraX.
5. Import file from ```working_directory/keymaera/graph.kyx```.
6. Run test in KeymaeraX. 
