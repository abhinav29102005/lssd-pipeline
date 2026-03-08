# Deploy to Railway via Docker Hub

Complete guide for deploying the Distributed HPC Job Scheduler using pre-built Docker images.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Hub](https://hub.docker.com/) account (`abhinav29102005`)
- [Railway](https://railway.app/) account
- Railway project created

---

## Part 1: Build & Push Backend Image

### Step 1: Build Backend Image

```bash
cd /home/bigboyaks/Projects/lssd-pipeline

# Build backend image
docker build -t abhinav29102005/lssd-backend:latest -f docker/backend.Dockerfile .
```

### Step 2: Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Push image
docker push abhinav29102005/lssd-backend:latest
```

**Verify on Docker Hub:**
Go to https://hub.docker.com/r/abhinav29102005/lssd-backend

---

## Part 2: Deploy Backend on Railway

### Step 3: Create Backend Service

1. Go to [railway.app/dashboard](https://railway.app/dashboard)
2. Click **"New"** → **"Service"**
3. Select **"Deploy from Docker Hub"**
4. Enter image: `abhinav29102005/lssd-backend:latest`
5. Click **Deploy**

### Step 4: Configure Backend Service

**Settings Tab:**

| Setting | Value |
|---------|-------|
| Service Name | `backend` |

**Variables Tab - Add All:**

| Variable | Value |
|----------|-------|
| `POSTGRES_DSN` | `postgresql+psycopg2://avnadmin:AVNS_0oiOBlbG_1jtm6DbXvV@bigboyaks-db-1024030440-bigboyaks-db.a.aivencloud.com:18099/defaultdb?sslmode=require` |
| `REDIS_URL` | Your Redis URL from Railway or external provider |
| `CLUSTER_SIZE` | `100` (or `500`, `1000` for larger clusters) |
| `SIMULATE_NODES` | `true` |
| `SCHEDULER_ALGORITHM` | `least_loaded` |
| `MAX_RETRIES` | `3` |
| `HEARTBEAT_INTERVAL` | `2` |
| `HEARTBEAT_TIMEOUT` | `8` |

**Optional Variables:**

| Variable | Value |
|----------|-------|
| `LOG_LEVEL` | `INFO` |
| `DEFAULT_NODE_CPU` | `8` |
| `DEFAULT_NODE_MEMORY_MB` | `32768` |
| `SCHEDULE_INTERVAL_SECONDS` | `0.2` |

6. Click **Deploy** (top right)

### Step 5: Verify Backend Deployment

1. Wait for green checkmark
2. Copy the backend URL from top of page (e.g., `https://backend-production-abc.up.railway.app`)
3. Test: Open `https://backend-production-abc.up.railway.app/health` in browser
4. Expected response:
   ```json
   {"status": "healthy", "algorithm": "least_loaded", "version": "2.0.0"}
   ```

---

## Part 3: Build & Push Dashboard Image

### Step 6: Build Dashboard with Backend URL

**Replace `https://backend-production-xxx.up.railway.app` with your actual backend URL:**

```bash
# Build dashboard with API URL
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://backend-production-xxx.up.railway.app \
  -t abhinav29102005/lssd-dashboard:latest \
  -f docker/dashboard.Dockerfile .
```

### Step 7: Push Dashboard to Docker Hub

```bash
# Push image
docker push abhinav29102005/lssd-dashboard:latest
```

---

## Part 4: Deploy Dashboard on Railway

### Step 8: Create Dashboard Service

1. Click **"New"** → **"Service"**
2. Select **"Deploy from Docker Hub"**
3. Enter image: `abhinav29102005/lssd-dashboard:latest`
4. Click **Deploy**

### Step 9: Configure Dashboard

**Settings Tab:**

| Setting | Action |
|---------|--------|
| Service Name | `dashboard` |
| Generate Domain | Click **"Generate Domain"** button |

5. Copy the generated dashboard URL

---

## Part 5: Verify Full Deployment

### Test Dashboard

1. Open dashboard URL: `https://dashboard-production-xyz.up.railway.app`
2. Should display **"Cluster Command Center"**
3. Verify metrics load:
   - Total Nodes
   - Active Nodes
   - Running Jobs
   - 3D Cluster Visualization

### Test API Endpoints

| Endpoint | URL |
|----------|-----|
| Health | `https://backend-xxx.up.railway.app/health` |
| API Docs | `https://backend-xxx.up.railway.app/docs` |
| Submit Job | `https://backend-xxx.up.railway.app/submit_job` |
| Cluster Status | `https://backend-xxx.up.railway.app/cluster_status` |

---

## Scale Cluster Size

To increase simulated nodes:

1. Go to **backend** service → **Variables**
2. Edit `CLUSTER_SIZE` to `500` or `1000`
3. Click **Deploy**

| Cluster Size | Recommended Memory |
|--------------|-------------------|
| 100 | 512 MB |
| 500 | 1 GB |
| 1000 | 2 GB |

---

## Update Deployment

### Update Backend

```bash
# Rebuild and push
docker build -t abhinav29102005/lssd-backend:latest -f docker/backend.Dockerfile .
docker push abhinav29102005/lssd-backend:latest

# Redeploy on Railway
cd /home/bigboyaks/Projects/lssd-pipeline
railway login
railway up --service backend
```

### Update Dashboard

```bash
# Rebuild with same backend URL
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://backend-xxx.up.railway.app \
  -t abhinav29102005/lssd-dashboard:latest \
  -f docker/dashboard.Dockerfile .

docker push abhinav29102005/lssd-dashboard:latest

# Redeploy
railway up --service dashboard
```

---

## Troubleshooting

### Backend Won't Start

**Check Logs:**
- Railway → backend service → **Logs** tab
- Look for PostgreSQL or Redis connection errors

**Common Issues:**

| Error | Fix |
|-------|-----|
| `Connection refused` to postgres | Verify `POSTGRES_DSN` has correct host |
| `Connection refused` to redis | Verify `REDIS_URL` is correct |
| `PORT not found` | Railway sets this automatically - don't override |

### Dashboard Shows API Error

1. Verify `NEXT_PUBLIC_API_URL` matches backend URL exactly
2. Check backend `/health` endpoint works
3. Verify CORS is enabled on backend (already configured in code)

### Build Fails

**Check:**
- Dockerfile path is correct: `/docker/backend.Dockerfile`
- Image exists on Docker Hub: `abhinav29102005/lssd-backend`
- Environment variables are set before deploying

---

## Quick Reference Commands

```bash
# Build backend
docker build -t abhinav29102005/lssd-backend:latest -f docker/backend.Dockerfile .

# Build dashboard (replace URL)
docker build --build-arg NEXT_PUBLIC_API_URL=https://backend-xxx.up.railway.app -t abhinav29102005/lssd-dashboard:latest -f docker/dashboard.Dockerfile .

# Push both
docker push abhinav29102005/lssd-backend:latest
docker push abhinav29102005/lssd-dashboard:latest

# Or push all tags
docker push -a abhinav29102005/lssd-backend
docker push -a abhinav29102005/lssd-dashboard
```

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│           Railway Project               │
│                                         │
│  ┌─────────────┐    ┌───────────────┐  │
│  │   Backend   │◄───│  PostgreSQL   │  │
│  │   Service   │    │   (Aiven)     │  │
│  │   :8000     │    └───────────────┘  │
│  │             │    ┌───────────────┐  │
│  │  FastAPI    │◄───│     Redis     │  │
│  │  Scheduler  │    │  (Railway)    │  │
│  │  Simulator  │    └───────────────┘  │
│  └──────┬──────┘                         │
│         │                               │
│         ▼                               │
│  ┌─────────────┐                       │
│  │  Dashboard  │                       │
│  │   Service   │                       │
│  │   :3000     │                       │
│  │             │                       │
│  │  Next.js    │                       │
│  │  Three.js   │                       │
│  └─────────────┘                       │
│                                         │
└─────────────────────────────────────────┘
```

---

## Support

- **Railway Docs:** https://docs.railway.app/
- **Docker Hub:** https://hub.docker.com/r/abhinav29102005/
- **Project Repo:** https://github.com/abhinav29102005/lssd-pipeline
