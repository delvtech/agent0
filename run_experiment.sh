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

# File to store environment variables
ENV_FILE="$EXPERIMENT_DIR/parameters.env"

# Write fixed environment variables to the file
echo "TERM_DAYS=365" > "$ENV_FILE"
echo "AMOUNT_OF_LIQUIDITY=10000000" >> "$ENV_FILE"
echo "FIXED_RATE=0.035" >> "$ENV_FILE"

# Generate random values within given ranges and append them to the file
echo "DAILY_VOLUME_PERCENTAGE_OF_LIQUIDITY=$(awk -v min=0.1 -v max=0.10 'BEGIN{srand(); print min+rand()*(max-min)}')" >> "$ENV_FILE"
echo "CURVE_FEE=$(awk -v min=0.001 -v max=0.01 'BEGIN{srand(); print min+rand()*(max-min)}')" >> "$ENV_FILE"

echo "FLAT_FEE=0.0001" >> "$ENV_FILE"
echo "GOVERNANCE_FEE=0.1" >> "$ENV_FILE"

# Set RANDSEED to the experiment ID and append it to the file
echo "RANDSEED=$NEXT_EXPERIMENT_ID" >> "$ENV_FILE"

# Run the experiment script within the experiment directory
(cd "$EXPERIMENT_DIR" && source "$ENV_FILE" && python ../../lib/agent0/examples/interactive_econ.py)