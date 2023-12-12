#!/bin/bash

# Base directory for experiments
EXPERIMENTS_DIR="./experiments"

# Create experiments directory if it doesn't exist
mkdir -p "$EXPERIMENTS_DIR"

# Determine the next experiment ID
NEXT_EXPERIMENT_ID=$(find "$EXPERIMENTS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)

# Create a new directory for this experiment
EXPERIMENT_DIR="$EXPERIMENTS_DIR/exp_$NEXT_EXPERIMENT_ID"
mkdir -p "$EXPERIMENT_DIR"

# Set fixed environment variables
export TERM_DAYS=365
export AMOUNT_OF_LIQUIDITY=10000000
export FIXED_RATE=0.035

# Generate random values within given ranges
export DAILY_VOLUME_PERCENTAGE_OF_LIQUIDITY=$(awk -v min=0.1 -v max=0.10 'BEGIN{srand(); print min+rand()*(max-min)}')
export CURVE_FEE=$(awk -v min=0.001 -v max=0.01 'BEGIN{srand(); print min+rand()*(max-min)}')

export FLAT_FEE=0.0001
export GOVERNANCE_FEE=0.1

# Set RANDSEED to the experiment ID
export RANDSEED=$NEXT_EXPERIMENT_ID

# Run the experiment script within the experiment directory
(cd "$EXPERIMENT_DIR" && python ../../lib/agent0/examples/interactive_econ.py)
