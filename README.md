# ⚡ Distributed HPC Job Scheduler

A production-quality distributed job scheduling platform capable of managing **100–1000 simulated compute nodes**, with Raft consensus, fault-tolerant scheduling, and a real-time **Next.js + Three.js WebGL dashboard**.

Resembles simplified versions of **Slurm**, **Kubernetes Scheduler**, **Apache Mesos**, and **CERN batch scheduling systems**.

---

## Architecture

```
                    ┌───────────────────────────┐
                    │        DASHBOARD          │
                    │   Next.js + TypeScript    │
                    │  WebGL + Framer Motion    │
                    └─────────────┬─────────────┘
                                  │ REST API (port 3000 → 8000)
                     ┌────────────▼────────────┐
                     │         FastAPI         │
                     │      Cluster API        │
                     │      (port 8000)        │
                     └────────────┬────────────┘
                                  │
                   ┌──────────────▼──────────────┐
                   │        CONTROL PLANE        │
                   │ (Kubernetes-style manager)  │
                   │                             │
                   │ ┌──────────┐  ┌──────────┐ │
                   │ │Scheduler │  │Controller│ │
                   │ └─────┬────┘  └─────┬────┘ │
                   │       │             │      │
                   │   ┌───▼─────────────▼───┐  │
                   │   │   Raft Consensus    │  │
                   │   │   Cluster State     │  │
                   │   └─────────────────────┘  │
                   └──────────────┬─────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
       ┌─────▼─────┐        ┌─────▼─────┐        ┌─────▼─────┐
       │ Worker #1 │        │ Worker #2 │  ...   │Worker #N  │
       └───────────┘        └───────────┘        └───────────┘

          ┌───────────────────────────────┐
          │     Redis (Job Queues)        │
          │ Pending / Running / Failed    │
          └───────────────────────────────┘

          ┌───────────────────────────────┐
          │     PostgreSQL (State)        │
          │ Jobs / Nodes / Metrics        │
          └───────────────────────────────┘
```

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11+, AsyncIO, FastAPI, Uvicorn |
| **Consensus** | Raft protocol (leader election, log replication) |
| **Data** | PostgreSQL 16, Redis 7 |
| **Dashboard** | Next.js 14, TypeScript, Three.js/WebGL, Framer Motion, Recharts, Tailwind CSS |
| **Infrastructure** | Docker, Docker Compose |

---

## Scheduling Algorithms

| Algorithm | Description |
|-----------|-------------|
| **FCFS** | First Come First Serve — assigns to first available node |
| **Priority** | Selects node with fewest jobs and most resources |
| **Round Robin** | Cycles through available nodes sequentially |
| **Least Loaded** | Picks node with minimum running jobs (default) |

Configure via `SCHEDULER_ALGORITHM` env var: `fcfs`, `priority`, `round_robin`, `least_loaded`.

---

## Fault Tolerance

- **Heartbeat monitoring** — Workers send heartbeats every 2s
- **Failure detection** — Nodes missing heartbeats for 8s marked failed
- **Job recovery** — Running jobs on failed nodes are requeued automatically
- **Retry with exponential backoff** — `max_retries=3`, delay = `1.5 × 2^(attempt-1)` seconds
- **Raft consensus** — Leader election ensures single scheduler authority

---

## Quick Start

### Docker Compose (Recommended)

```bash
docker compose up --build
```

Services:
- **API**: http://localhost:8000
- **Dashboard**: http://localhost:3000
- Scale workers: `docker compose up --scale worker_nodes=100`

### Render Blueprint (Cloud Deployment)

The repository includes a `render.yaml` blueprint optimized for deploying to Render.

1. Create a free **PostgreSQL** database and a free **Redis** instance (e.g., Upstash or Render Redis).
2. Connect your GitHub repository to Render and use the **Blueprint** feature to deploy `render.yaml`.
3. Provide your `POSTGRES_DSN` and `REDIS_URL` in the Render dashboard when prompted.

*Note: The API and Dashboard are configured for the Free Web Services tier. Background workers map to the Starter tier.*

### Local Development

```bash
# Backend
./setup.sh
source venv/bin/activate
python -m src.main

# API (separate terminal)
uvicorn src.api.job_api:app --host 0.0.0.0 --port 8000

# Dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```

---

## API Endpoints

### Jobs

```bash
# Submit a job
curl -X POST http://localhost:8000/submit_job \
  -H 'Content-Type: application/json' \
  -d '{"task_type":"compute_pi","required_cpu":2,"required_memory":1024,"priority":10,"execution_time":5}'

# Get job status
curl http://localhost:8000/job/{job_id}

# List jobs (with filters)
curl "http://localhost:8000/jobs?status=running&limit=50"

# Cancel a job
curl -X DELETE http://localhost:8000/job/{job_id}
```

### Cluster

```bash
# Cluster status
curl http://localhost:8000/cluster_status

# List nodes
curl "http://localhost:8000/nodes?status=available&limit=200"

# Metrics history
curl "http://localhost:8000/metrics?limit=100"

# Health check
curl http://localhost:8000/health
```

---

## Dashboard Pages

| Route | Description |
|-------|-------------|
| `/` | Cluster overview — KPIs, 3D WebGL cluster map, node grid, utilization charts |
| `/nodes` | Node health — status filters, 2D grid visualization, details table |
| `/jobs` | Job queue — Gantt timeline, status breakdown, job explorer |
| `/metrics` | Cluster metrics — utilization, throughput, node health time series |
| `/submit` | Job submission — task type selector, resource config, batch submit |

---

## Load Testing

```bash
# Submit 1000 jobs across 50 threads
python -m src.utils.load_test
```

Measures scheduling latency, queue wait time, and P95 end-to-end time.

---

## Project Structure

```
lssd-pipeline/
├── src/
│   ├── control_plane/         # Raft consensus + Kubernetes controller
│   │   ├── raft_consensus.py  # Raft state machine, leader election, log replication
│   │   ├── leader_election.py # High-level leadership abstraction
│   │   └── controller.py      # Reconciliation loop (desired vs actual state)
│   ├── scheduler/             # Job scheduling engine
│   │   ├── scheduler.py       # Core scheduling loop
│   │   ├── scheduling_algorithms.py  # FCFS, Priority, Round Robin, Least Loaded
│   │   ├── job_queue.py       # Redis-backed priority queue
│   │   └── retry_manager.py   # Exponential backoff retries
│   ├── cluster/               # Cluster node management
│   │   ├── node_manager.py    # Node CRUD + heartbeat tracking
│   │   ├── cluster_simulator.py  # 100-1000 virtual nodes
│   │   └── node.py            # Node domain model
│   ├── execution/             # Job execution
│   │   ├── worker.py          # Worker process
│   │   └── job_executor.py    # Simulated HPC tasks (Pi, Matrix, Monte Carlo)
│   ├── fault_tolerance/       # Fault detection & recovery
│   │   ├── failure_detector.py
│   │   ├── heartbeat.py
│   │   └── recovery_manager.py
│   ├── database/              # PostgreSQL models & session management
│   ├── api/                   # FastAPI REST endpoints
│   └── utils/                 # Config, load testing
├── dashboard/                 # Next.js 14 + Three.js WebGL dashboard
│   ├── app/                   # App Router pages
│   ├── components/            # Cluster3D, NodeGrid, JobTimeline, MetricsCharts
│   └── lib/                   # API client
├── docker/                    # Dockerfiles
├── docker-compose.yml
└── requirements.txt
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_SIZE` | 100 | Number of simulated nodes |
| `SCHEDULER_ALGORITHM` | least_loaded | Scheduling strategy |
| `MAX_RETRIES` | 3 | Max job retry attempts |
| `HEARTBEAT_INTERVAL` | 2 | Heartbeat period (seconds) |
| `HEARTBEAT_TIMEOUT` | 8 | Node failure threshold (seconds) |
| `JOB_TIMEOUT` | 120 | Max job execution time |
| `JOB_FAILURE_RATE` | 0.07 | Synthetic failure probability |
| `SIMULATE_NODES` | true | Enable cluster simulation |

---

## Advanced Features (TODO)

- [ ] Auto-scaling cluster based on queue pressure
- [ ] GPU job scheduling
- [ ] Priority fairness queues
- [ ] Job preemption
- [ ] Job dependency DAG
- [ ] Kubernetes deployment (Helm chart)
- [ ] Job checkpointing and recovery
