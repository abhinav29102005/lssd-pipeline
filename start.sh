#!/bin/bash
# start.sh - Runs both the Scheduler Core and API Server in a single container
# This is optimized for free-tier deployments (e.g. Northflank) where service limits apply.

# Exit on error
set -e

echo "Starting Distributed HPC Scheduler (All-in-One Mode)..."

# Ensure SIMULATE_NODES is enabled so the scheduler also runs worker nodes internally
export SIMULATE_NODES=${SIMULATE_NODES:-"true"}
export CLUSTER_SIZE=${CLUSTER_SIZE:-"100"}

# Start the scheduler core in the background
python -m src.main &
SCHEDULER_PID=$!

echo "Scheduler started in background (PID: $SCHEDULER_PID)"

# Start the FastAPI server in the foreground
echo "Starting API Server on port 8000..."
uvicorn src.api.job_api:app --host 0.0.0.0 --port 8000

# If the API server exits, trap it and kill the background scheduled
kill $SCHEDULER_PID
