# Capstone V3: Setup & Deployment Guide

**Version:** 3.0.0  
**Platforms:** macOS, Linux, Windows (WSL2)  
**Time Estimate:** 30-45 minutes

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git
- 15 GB free disk space (models + checkpoints)
- NVIDIA GPU with 6+ GB VRAM (recommended; CPU fallback available)

### One-Command Setup

**macOS/Linux:**
```bash
cd backend && chmod +x scripts/bootstrap_capstone_models.ps1 && \
pip install -r requirements.txt -r requirements_capstone_v3.txt && \
pip install git+https://github.com/facebookresearch/sam2.git && \
git clone https://github.com/advimman/lama.git external/lama && \
cd external/lama && pip install -r requirements.txt && cd ../.. && \
python scripts/verify_capstone_models.py
```

**Windows (PowerShell as Admin):**
```powershell
cd backend
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
.\scripts\bootstrap_capstone_models.ps1
python scripts\verify_capstone_models.py
```

---

## 📦 Detailed Setup Steps

### Step 1: Clone Repository
```bash
git clone <repo-url>
cd system-design-graph-rag-reasoning-image-resource-management-software-main
```

### Step 2: Backend Setup

**Install Python dependencies:**
```bash
cd backend

# Base dependencies
pip install -r requirements.txt

# ML dependencies
pip install -r requirements_capstone_v3.txt

# SAM2 (from GitHub)
pip install git+https://github.com/facebookresearch/sam2.git

# LaMa (git clone + local install)
git clone https://github.com/advimman/lama.git external/lama
cd external/lama
pip install -r requirements.txt
cd ../..
```

**Download model checkpoints:**
```bash
# SAM2 (2.6 GB)
mkdir -p checkpoints
cd checkpoints
# Download from: https://dl.fbaipublicfiles.com/segment_anything_2/sam2_hiera_large.pt
wget https://dl.fbaipublicfiles.com/segment_anything_2/sam2.1_hiera_large.pt
cd ..

# Big-LaMa (4.3 GB)
mkdir -p models
cd models
# Download from: https://github.com/advimman/lama#pretrained-models
# Extract to: models/big-lama/
cd ..
```

**Configure environment:**
```bash
# Create backend/.env
cat > .env << 'EOF'
# SAM2
CAPSTONE_SAM2_CHECKPOINT=checkpoints/sam2.1_hiera_large.pt
CAPSTONE_SAM2_CONFIG=configs/sam2.1/sam2.1_hiera_l.yaml

# LaMa
CAPSTONE_LAMA_REPO_PATH=external/lama
CAPSTONE_LAMA_MODEL_PATH=models/big-lama
CAPSTONE_LAMA_PYTHON=python
CAPSTONE_LAMA_REFINER_GPU_IDS=0,
CAPSTONE_LAMA_ALLOW_WINDOWS_REFINE=false

# Device
CAPSTONE_DEVICE=auto
CAPSTONE_ALLOW_MOCK_FALLBACKS=false

# Neo4j (optional)
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j
EOF
```

**Verify setup:**
```bash
python scripts/verify_capstone_models.py
```

Expected output:
```json
{
  "sam2": {"ready": true, "device": "cuda"},
  "lama": {"ready": true, "device": "cuda"}
}
```

### Step 3: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Browser opens at `http://localhost:5173`

### Step 4: Start Backend

```bash
cd backend
python run_server.py
```

Backend runs at `http://localhost:8000`

### Step 5: Verify Integration

Open browser at `http://localhost:5173/capstone-studio` and:
1. Upload test image
2. Click to segment object (SAM2)
3. Remove object (LaMa inpaints)
4. Check edit history

---

## 🗺️ Directory Checklist

After setup, verify:
```
backend/
├─ checkpoints/
│  └─ sam2.1_hiera_large.pt (2.6 GB) ✓
├─ models/
│  └─ big-lama/ (4.3 GB) ✓
├─ external/
│  └─ lama/ (git clone) ✓
├─ uploads/capstone/
│  ├─ originals/ ✓
│  ├─ masks/ ✓
│  ├─ canvas_versions/ ✓
│  └─ scenes/ ✓
├─ .env ✓
├─ requirements.txt ✓
├─ requirements_capstone_v3.txt ✓
└─ run_server.py ✓

frontend/
├─ node_modules/ ✓
├─ src/ ✓
├─ package.json ✓
└─ vite.config.js ✓
```

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAPSTONE_SAM2_CHECKPOINT` | `checkpoints/sam2.1_hiera_large.pt` | SAM2 weights path |
| `CAPSTONE_SAM2_CONFIG` | `configs/sam2.1/sam2.1_hiera_l.yaml` | SAM2 config |
| `CAPSTONE_LAMA_REPO_PATH` | `external/lama` | LaMa git clone path |
| `CAPSTONE_LAMA_MODEL_PATH` | `models/big-lama` | Big-LaMa weights path |
| `CAPSTONE_DEVICE` | `auto` | Device: "auto" \| "cuda" \| "cpu" |
| `CAPSTONE_ALLOW_MOCK_FALLBACKS` | `false` | Use mock models if real ones fail |
| `NEO4J_URL` | `bolt://localhost:7687` | Neo4j connection (optional) |

### Backend Config (FastAPI)

**File:** `backend/app/main.py`
```python
app = FastAPI(
    title="Capstone V3",
    description="Graph-Augmented Image Manipulation",
    version="3.0.0"
)

app.include_router(v3_capstone.router)
```

### Frontend Config (Vite)

**File:** `frontend/vite.config.js`
```javascript
export default {
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'  // Proxy API calls
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
}
```

---

## 🚨 Troubleshooting

### SAM2 Not Found
```bash
# Solution: Install from GitHub
pip install git+https://github.com/facebookresearch/sam2.git
```

### LaMa Subprocess Timeout
```bash
# Solution: Disable refinement (edit InpaintTuning)
enable_refinement: false
```

### CUDA Out of Memory
```bash
# Solution 1: Use smaller model
CAPSTONE_SAM2_CHECKPOINT=checkpoints/sam2_hiera_base.pt

# Solution 2: Force CPU
CAPSTONE_DEVICE=cpu

# Solution 3: Reduce batch size (if batch operations added)
```

### Neo4j Connection Error
```bash
# Solution: Start Neo4j locally or use Aura
docker run --name neo4j -p 7687:7687 neo4j:5.17
```

### Frontend Can't Reach Backend
```bash
# Solution: Check CORS headers in backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

---

## 📊 Resource Requirements

| Component | RAM | VRAM | Disk |
|-----------|-----|------|------|
| Backend (minimal) | 2GB | - | 1GB |
| SAM2 model | 2GB | 6GB | 2.6GB |
| LaMa model | 3GB | 8-12GB | 4.3GB |
| **Total** | **7GB** | **12-18GB** | **8GB** |

**Recommendation:** 16GB RAM, RTX 2080 Ti or better

---

## 🌐 Production Deployment

### Railway (Backend)
```bash
# 1. Create Railway project
# 2. Connect GitHub repo
# 3. Set environment variables in Dashboard
# 4. Deploy: git push
```

### Vercel (Frontend)
```bash
# 1. Connect GitHub repo
# 2. Build command: cd frontend && npm run build
# 3. Output directory: frontend/dist
# 4. Deploy: auto on push
```

### S3/Cloudflare R2 (Storage)
```python
# Configure in backend/app/rendering/storage.py
S3_BUCKET = "capstone-storage"
S3_REGION = "us-east-1"
S3_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("R2_SECRET_KEY")
```

---

## ✅ Post-Setup Verification

```bash
# 1. Backend health check
curl http://localhost:8000/health

# 2. V3 capabilities
curl http://localhost:8000/api/v3/capabilities

# 3. Frontend build
cd frontend && npm run build

# 4. Run tests
pytest tests/
npm run test:unit

# 5. Quick E2E flow
# - Upload image: POST /api/v3/scenes/upload
# - Segment: POST /api/v3/scenes/{id}/segment-click
# - Remove: POST /api/v3/scenes/{id}/remove-object
```

---

## 📝 Summary

**Setup complete when:**
✅ Backend runs at localhost:8000  
✅ Frontend runs at localhost:5173  
✅ SAM2 and LaMa load successfully  
✅ End-to-end flow works (upload → segment → remove)  
✅ Neo4j synced (optional)

---

**Next:** Read [08_TESTING_V3.md](./08_TESTING_V3.md) for comprehensive testing strategy.
