# Railway Deployment Guide

## Distributed HPC Job Scheduler - Railway Cloud Deployment

This guide covers deploying the Distributed HPC Job Scheduler to Railway's cloud platform.

### Architecture

The system consists of two Railway services:

1. **Backend Service** (`docker/backend.Dockerfile`)
   - FastAPI REST API
   - Scheduler loop
   - Raft consensus control plane
   - Cluster simulator (100-1000 nodes)

2. **Dashboard Service** (`docker/dashboard.Dockerfile`)
   - Next.js 14 frontend
   - Three.js WebGL visualization
   - Real-time cluster monitoring

### Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli) installed
- Railway account
- PostgreSQL database (Aiven or Railway)
- Redis instance (Upstash or Railway)

### Environment Variables

#### Backend Service

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Railway-assigned port | 8000 |
| `POSTGRES_DSN` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection URL | Required |
| `SIMULATE_NODES` | Enable node simulation | true |
| `CLUSTER_SIZE` | Number of simulated nodes | 100 |
| `SCHEDULER_ALGORITHM` | Scheduling algorithm | least_loaded |
| `MAX_RETRIES` | Job retry count | 3 |
| `HEARTBEAT_INTERVAL` | Node heartbeat interval (seconds) | 2 |
| `HEARTBEAT_TIMEOUT` | Node timeout threshold (seconds) | 8 |
| `LOG_LEVEL` | Logging level | INFO |

#### Dashboard Service

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | https://backend.up.railway.app |

### Deployment Steps

#### 1. Install Railway CLI

```bash
npm install -g @railway/cli
# or
brew install railway
```

#### 2. Login to Railway

```bash
railway login
```

#### 3. Initialize Project

```bash
# From the repository root
railway init
```

Select "Create a new project" or link to an existing project.

#### 4. Provision Databases

##### Option A: Railway-managed databases

```bash
# Add PostgreSQL
railway add --database postgres

# Add Redis
railway add --database redis
```

##### Option B: External databases (Aiven)

Use the provided PostgreSQL DSN and Redis URL from your external provider.

#### 5. Deploy Backend Service

```bash
# Create backend service from Dockerfile
railway up --service backend --dockerfile docker/backend.Dockerfile

# Set environment variables
railway variables --service backend

# Example variables:
# POSTGRES_DSN=postgresql+psycopg2://user:pass@host:port/db?sslmode=require
# REDIS_URL=rediss://default:pass@host:port
# CLUSTER_SIZE=100
# SIMULATE_NODES=true
```

#### 6. Deploy Dashboard Service

```bash
# Get backend URL first
railway status --service backend

# Create dashboard service
railway up --service dashboard --dockerfile docker/dashboard.Dockerfile

# Set the API URL
railway variables --service dashboard NEXT_PUBLIC_API_URL="https://backend-<project>.up.railway.app"
```

> **Note:** Replace `NEXT_PUBLIC_API_URL` with your actual backend service URL.

#### 7. Configure CORS (if needed)

The FastAPI backend already allows all origins (`allow_origins=["*"]`) for development. For production, update `src/api/job_api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-dashboard.up.railway.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Scaling Cluster Size

To simulate larger clusters (up to 1000 nodes):

```bash
railway variables --service backend CLUSTER_SIZE=1000
railway up --service backend
```

The cluster simulator will automatically register the specified number of virtual nodes.

### Monitoring

#### Health Endpoints

- Backend: `https://<backend-url>/health`
- Dashboard: `https://<dashboard-url>` (implicit health via HTTP 200)

#### Railway CLI Commands

```bash
# View logs
railway logs --service backend
railway logs --service dashboard

# View service status
railway status

# Open dashboard in browser
railway open --service dashboard
```

### API Endpoints

Once deployed, the backend exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/submit_job` | POST | Submit a single job |
| `/submit_jobs` | POST | Submit batch jobs |
| `/job/{id}` | GET | Get job status |
| `/jobs` | GET | List jobs |
| `/job/{id}` | DELETE | Cancel job |
| `/cluster_status` | GET | Cluster summary |
| `/nodes` | GET | List nodes |
| `/metrics` | GET | Cluster metrics history |
| `/docs` | GET | Swagger API documentation |

### Troubleshooting

#### Database Connection Issues

Ensure `POSTGRES_DSN` uses the correct format:
```
postgresql+psycopg2://user:password@host:port/database?sslmode=require
```

For Aiven PostgreSQL, always include `?sslmode=require`.

#### Redis Connection Issues

Verify `REDIS_URL` format:
```
rediss://username:password@host:port/0
```

Note `rediss://` (with SSL) for managed Redis services.

#### Port Binding

Railway sets the `PORT` environment variable automatically. The start script uses this variable to bind the FastAPI server.

#### Memory Limits

For 1000-node simulations, ensure your Railway service has sufficient memory:
- 100 nodes: ~512MB
- 500 nodes: ~1GB
- 1000 nodes: ~2GB

### File Structure

```
lssd-pipeline/
├── docker/
│   ├── backend.Dockerfile      # Railway backend service
│   ├── dashboard.Dockerfile      # Railway dashboard service
│   └── ...                     # Other Dockerfiles
├── railway.json                # Railway configuration (optional)
├── start.sh                    # Backend startup script
├── requirements.txt            # Python dependencies
├── dashboard/
│   ├── next.config.js          # Next.js config with Railway settings
│   └── ...                     # Dashboard source
└── src/
    ├── api/job_api.py          # FastAPI application
    ├── scheduler/scheduler.py  # Scheduler service
    ├── control_plane/          # Raft consensus + controller
    └── cluster/                # Node simulator
```

### Updating Deployment

To deploy updates:

```bash
# Commit changes
git add .
git commit -m "Update deployment"

# Redeploy
railway up
```

Or enable auto-deploy on git push in Railway dashboard.

### Alternative: Deploy via Railway Dashboard

1. Create new project in [Railway Dashboard](https://railway.app/dashboard)
2. Connect GitHub repository
3. Add PostgreSQL and Redis services
4. Create services from Dockerfiles:
   - Service 1: Backend (docker/backend.Dockerfile)
   - Service 2: Dashboard (docker/dashboard.Dockerfile)
5. Set environment variables
6. Deploy

### Support

For Railway-specific issues:
- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)

For application issues, check the logs:
```bash
railway logs --service backend --follow
```
