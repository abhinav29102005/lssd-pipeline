#!/bin/bash
# Startup script for Railway backend service
# Launches all backend components: scheduler, control plane, cluster simulator, and API

set -e

# Logging setup
LOG_LEVEL=${LOG_LEVEL:-INFO}
echo "=== Distributed HPC Job Scheduler Startup ==="
echo "Log Level: $LOG_LEVEL"
echo "Port: $PORT"
echo "Cluster Size: ${CLUSTER_SIZE:-100}"
echo "Simulate Nodes: ${SIMULATE_NODES:-true}"
echo "Scheduler Algorithm: ${SCHEDULER_ALGORITHM:-least_loaded}"
echo "==========================================="

# Validate required environment variables
if [ -z "$POSTGRES_DSN" ]; then
    echo "WARNING: POSTGRES_DSN not set. Using default local configuration."
fi

if [ -z "$REDIS_URL" ]; then
    echo "WARNING: REDIS_URL not set. Using default redis://localhost:6379/0"
fi

if [ -z "$PORT" ]; then
    echo "ERROR: PORT environment variable is required by Railway"
    exit 1
fi

# Function to cleanup processes on exit
cleanup() {
    echo "Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Initialize database schema
echo "=== Initializing Database ==="
python -c "
from src.database.db import init_db
init_db()
print('Database initialized successfully')
"

# Start the scheduler service (scheduling loop + metrics collection)
echo "=== Starting Scheduler Service ==="
python -m src.scheduler.scheduler &
SCHEDULER_PID=$!
echo "Scheduler started (PID: $SCHEDULER_PID)"

# Start the control plane (Raft consensus + cluster controller)
echo "=== Starting Control Plane ==="
python -m src.control_plane.controller &
CONTROLLER_PID=$!
echo "Control plane started (PID: $CONTROLLER_PID)"

# Start the cluster simulator if simulation is enabled
if [ "${SIMULATE_NODES:-true}" = "true" ]; then
    echo "=== Starting Cluster Simulator ==="
    python -m src.cluster.cluster_simulator &
    SIMULATOR_PID=$!
    echo "Cluster simulator started (PID: $SIMULATOR_PID)"
else
    echo "Cluster simulation disabled (SIMULATE_NODES != true)"
fi

# Wait a moment for background services to initialize
sleep 2

# Start the FastAPI server on Railway's PORT
echo "=== Starting FastAPI Server on port $PORT ==="
echo "Health endpoint: http://0.0.0.0:$PORT/health"
echo "API docs: http://0.0.0.0:$PORT/docs"

# Run uvicorn in the foreground so the container keeps running
exec uvicorn src.api.job_api:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level "${LOG_LEVEL,,}" \
    --access-log \
    --workers 1
