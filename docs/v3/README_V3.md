# Capstone V3: Complete Documentation Index

**Version:** 3.0  
**Last Updated:** 2025  
**Status:** Production Ready  

---

## 🚀 Quick Start (5 Minutes)

### Installation

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Download models (6-8 GB disk space)
python -c "from app.capstone.inference import SAM2Segmenter; SAM2Segmenter()" 
# Downloads SAM2 checkpoint to ~/.cache

# Frontend
cd ../frontend
npm install
npm run dev  # Runs on localhost:5173
```

### Run Development Server

```bash
# Terminal 1: Backend
cd backend
python run_server.py  # Runs on localhost:8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Visit:** http://localhost:5173

### First Scene

1. **Upload Image** → Click upload button → Select any image
2. **Segment** → Click on object in image → Shows blue mask overlay
3. **Remove** → Click "Remove Object" → Shows inpainted result
4. **Undo** → View history in right panel → Click to restore

---

## 📚 Documentation Suite

### Overview (Start Here)

| Document | Purpose | Audience | Read Time |
|----------|---------|----------|-----------|
| [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md) | Executive summary, key concepts, data flow | Everyone | 15 min |
| [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md) | Component design, layering, storage topology | Architects, Backend devs | 20 min |
| [02_SCHEMA_V3.md](./02_SCHEMA_V3.md) | All data models with examples | Backend devs, Data engineers | 20 min |
| [03_API_V3.md](./03_API_V3.md) | REST API endpoints with JSON examples | Frontend devs, API consumers | 25 min |

### Deep Dive (Detailed Implementation)

| Document | Purpose | Audience | Read Time |
|----------|---------|----------|-----------|
| [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) | SAM2, LaMa algorithms, tuning parameters | ML engineers, researchers | 25 min |
| [05_FRONTEND_V3.md](./05_FRONTEND_V3.md) | React components, state management, styling | Frontend devs | 20 min |
| [06_INTEGRATION_GUIDE_V3.md](./06_INTEGRATION_GUIDE_V3.md) | Multi-component workflows, error handling | Full-stack devs | 20 min |
| [07_SETUP_V3.md](./07_SETUP_V3.md) | Installation, configuration, deployment | DevOps, System admins | 20 min |
| [08_TESTING_V3.md](./08_TESTING_V3.md) | Unit/integration/E2E tests, CI/CD | QA, Backend devs | 20 min |

**Total Documentation:** ~35,000 words across 9 files

---

## 🎯 Find What You Need

### By Role

**Frontend Developer**
1. Start: [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md) - Overview
2. Read: [03_API_V3.md](./03_API_V3.md) - API endpoints (section "Request/Response Examples")
3. Read: [05_FRONTEND_V3.md](./05_FRONTEND_V3.md) - Component architecture
4. Read: [06_INTEGRATION_GUIDE_V3.md](./06_INTEGRATION_GUIDE_V3.md) - Multi-component workflows

**Backend Developer**
1. Start: [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md)
2. Read: [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md) - Component design
3. Read: [02_SCHEMA_V3.md](./02_SCHEMA_V3.md) - Data models (copy these for your code)
4. Read: [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) - ML integration details
5. Implement: [03_API_V3.md](./03_API_V3.md) - API endpoints

**ML Engineer**
1. Start: [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md)
2. Read: [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) - SAM2/LaMa algorithms
3. Reference: [02_SCHEMA_V3.md](./02_SCHEMA_V3.md) - SegmentationTuning, InpaintTuning configs
4. Benchmark: [08_TESTING_V3.md](./08_TESTING_V3.md) - Performance test suite

**DevOps / System Admin**
1. Start: [07_SETUP_V3.md](./07_SETUP_V3.md) - Installation and deployment
2. Reference: [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md) - System requirements
3. Implement: [06_INTEGRATION_GUIDE_V3.md](./06_INTEGRATION_GUIDE_V3.md) - Deployment checklist
4. Monitor: [08_TESTING_V3.md](./08_TESTING_V3.md) - Monitoring section

**Researcher / Data Scientist**
1. Start: [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md) - System design
2. Read: [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) - Model integration details
3. Reference: [08_TESTING_V3.md](./08_TESTING_V3.md) - Evaluation metrics

---

## 🔑 Core Concepts

### What is V3?

**Graph-Augmented Interactive Image Editing System**

Users click on objects in images → System segments using SAM2 → Users remove objects → System inpaints using LaMa with spatial context → Full edit history preserved in event sourcing format.

### Key Innovations

| Feature | Purpose | Status |
|---------|---------|--------|
| **SAM2 Integration** | Zero-shot click-based segmentation | ✅ Implemented |
| **Spatial Graphs** | Track object relationships (above, left_of, overlaps) | ✅ Implemented |
| **Graph-Aware Inpainting** | LaMa uses neighbor info for better removal | ✅ Implemented |
| **Immutable Event Sourcing** | Full reproducible edit history | ✅ Implemented |
| **Freehand Segmentation** | Lasso/brush-based alternate to clicks | ✅ Implemented |
| **Accuracy Presets** | Segmentation tuning profiles | ✅ Implemented |

### System Stack

```
Frontend: React 18 + TypeScript + Tailwind CSS + Vite
Backend: FastAPI + Python 3.11 + PyTorch 2.6 + CUDA
Models: SAM2 (2.6GB) + Big-LaMa (4.3GB)
Storage: JSON (primary) + Neo4j (optional) + S3/Local
Database: SQLite (queue) + Neo4j Aura (optional)
```

---

## 📋 Common Tasks

### Upload and Segment

**API Endpoint:** `POST /api/v3/scenes`

```bash
curl -X POST http://localhost:8000/api/v3/scenes \
  -F "image=@image.jpg" \
  -F "label=living room"
```

**Response:**
```json
{
  "scene_id": "scene_a1b2c3",
  "canvas_image_url": "http://localhost:8000/uploads/...",
  "objects": []
}
```

**Frontend:**
```typescript
const response = await v3Client.createScene(image, "my scene");
const { scene_id, canvas_image_url } = response;
```

---

### Click to Segment

**API Endpoint:** `POST /api/v3/scenes/{id}/segment-click`

```bash
curl -X POST http://localhost:8000/api/v3/scenes/scene_a1b2c3/segment-click \
  -H "Content-Type: application/json" \
  -d '{
    "click_x": 0.5,
    "click_y": 0.3,
    "label": "sofa",
    "tuning": {
      "dilate_px": 2,
      "erode_px": 0,
      "multimask_strategy": "largest_area"
    }
  }'
```

**Response:**
```json
{
  "object_id": "obj_xyz",
  "mask_url": "http://localhost:8000/uploads/masks/sofa_xyz.png",
  "bbox": {"x": 100, "y": 50, "w": 200, "h": 150},
  "confidence": 0.95,
  "latency_ms": 1234
}
```

---

### Remove Object

**API Endpoint:** `POST /api/v3/scenes/{id}/remove-object`

```bash
curl -X POST http://localhost:8000/api/v3/scenes/scene_a1b2c3/remove-object \
  -H "Content-Type: application/json" \
  -d '{
    "object_id": "obj_xyz",
    "record_event": true,
    "tuning": {
      "mask_dilate_px": 4,
      "neighbor_limit": 5,
      "enable_refinement": true
    }
  }'
```

**Response:**
```json
{
  "new_canvas_image_url": "http://localhost:8000/uploads/...",
  "edit_event_id": "edit_removal_123",
  "inpaint_time_ms": 7234
}
```

---

### View Edit History

**API Endpoint:** `GET /api/v3/scenes/{id}/history`

```bash
curl http://localhost:8000/api/v3/scenes/scene_a1b2c3/history
```

**Response:**
```json
{
  "events": [
    {
      "event_id": "init_123",
      "event_type": "INIT",
      "timestamp": "2025-01-15T10:00:00Z",
      "canvas_version": {...}
    },
    {
      "event_id": "edit_removal_1",
      "event_type": "REMOVE_OBJECT",
      "object_id": "obj_xyz",
      "before_state_json": {...},
      "after_state_json": {...},
      "canvas_version": {...}
    }
  ]
}
```

---

## 🔧 API Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v3/capabilities` | Get system capabilities (SAM2/LaMa available?) |
| POST | `/api/v3/scenes` | Create new scene (upload image) |
| GET | `/api/v3/scenes/{id}` | Get scene details |
| POST | `/api/v3/scenes/{id}/segment-click` | Segment from click |
| POST | `/api/v3/scenes/{id}/segment-freehand` | Segment from freehand brush |
| POST | `/api/v3/scenes/{id}/remove-object` | Remove object via inpainting |
| GET | `/api/v3/scenes/{id}/objects` | List all objects in scene |
| GET | `/api/v3/scenes/{id}/text-regions` | List detected text regions |
| GET | `/api/v3/scenes/{id}/edits` | List all edit events |
| POST | `/api/v3/scenes/{id}/aspect-ratio` | Adjust aspect ratio |
| GET | `/api/v3/scenes/{id}/history` | Get full edit history |
| GET | `/api/v3/scenes/{id}/inpaint-context/{object_id}` | Get context for inpainting |

**Full spec:** See [03_API_V3.md](./03_API_V3.md)

---

## 🐛 Troubleshooting

### "CUDA not found" / "No GPU detected"

**Fix:** Check [07_SETUP_V3.md](./07_SETUP_V3.md#troubleshooting) section "GPU Setup"

```bash
python -c "import torch; print(torch.cuda.is_available())"  # Should print True
```

### "SAM2 segmentation is slow (>5s)"

**Fix:** Running on CPU. Install PyTorch with CUDA:

```bash
pip uninstall torch -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### "LaMa inpainting produces artifacts"

**Fix:** Tune inpaint parameters in [02_SCHEMA_V3.md](./02_SCHEMA_V3.md#inpainttuning):

```python
tuning = InpaintTuning(
    mask_dilate_px=8,           # Increase dilation
    enable_refinement=True,      # Enable post-processing
    refine_n_iters=5            # More refinement iterations
)
```

### "Scene not saving" / "JSON errors"

**Fix:** Check disk space and file permissions:

```bash
ls -la backend/uploads/capstone/scenes/  # Directory exists?
df -h  # Disk space available?
```

### "S3 upload failing"

**Fix:** Check S3 credentials in `.env`:

```bash
# backend/.env
S3_BUCKET=capstone-storage
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

**More help:** See [07_SETUP_V3.md#troubleshooting](./07_SETUP_V3.md)

---

## 📊 Data Models (Quick Peek)

### SceneNode
```python
{
  "scene_id": "scene_123",
  "created_at": "2025-01-15T10:00:00Z",
  "modified_at": "2025-01-15T10:05:00Z",
  "canvas_width": 1920,
  "canvas_height": 1080,
  "metadata": {"source": "upload", "format": "jpg"}
}
```

### ImageObjectNode
```python
{
  "object_id": "obj_123",
  "scene_id": "scene_123",
  "label": "sofa",
  "mask_url": "https://s3.../sofa_mask.png",
  "bbox": {"x": 100, "y": 50, "w": 200, "h": 150},
  "created_at": "2025-01-15T10:01:00Z"
}
```

### EditEventNode
```python
{
  "event_id": "edit_removal_1",
  "scene_id": "scene_123",
  "event_type": "REMOVE_OBJECT",
  "delta_json": {"object_id": "obj_123"},
  "before_state_json": {...scene state before...},
  "after_state_json": {...scene state after...},
  "canvas_version_id": "version_2",
  "created_at": "2025-01-15T10:01:30Z"
}
```

**Full models:** [02_SCHEMA_V3.md](./02_SCHEMA_V3.md)

---

## 🧪 Testing

### Run All Tests

```bash
cd backend
pytest -v                    # All tests
pytest tests/capstone/ -v   # Only V3 tests
pytest --cov=app           # With coverage
```

### Run Frontend Tests

```bash
cd frontend
npm test                     # Jest
npm run test:e2e           # Playwright
```

**Test guide:** [08_TESTING_V3.md](./08_TESTING_V3.md)

---

## 📈 Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| SAM2 segmentation (cached) | < 2s | 1.2s |
| SAM2 segmentation (cold) | < 5s | 3.5s |
| LaMa inpainting | < 10s | 7.2s |
| API response (non-ML) | < 500ms | 150ms |
| Frontend bundle size | < 500KB | 380KB |
| JSON scene file size | < 50MB | 5MB (typical) |

---

## 🚀 Deployment

### Production Checklist

See [06_INTEGRATION_GUIDE_V3.md#-deployment-checklist](./06_INTEGRATION_GUIDE_V3.md) for full checklist.

### Docker

```dockerfile
# backend/Dockerfile
FROM pytorch/pytorch:2.6-cuda12.1-devel-ubuntu22.04
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ .
CMD ["python", "run_server.py"]
```

### Deploy to Railway

```bash
# 1. Push code to Git
git add .
git commit -m "Deploy V3"
git push

# 2. Connect Railway project
railway link

# 3. Set environment variables
railway variables set S3_BUCKET=capstone-storage
railway variables set DEVICE=cuda

# 4. Deploy
railway up
```

**Full deployment:** [07_SETUP_V3.md#deployment](./07_SETUP_V3.md)

---

## 📖 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│          CapstoneStudio (React + TypeScript)            │
│          - Image upload & canvas                        │
│          - Click/brush segmentation UI                  │
│          - Edit history panel                           │
│                                                         │
└────────────────────┬──────────────────────────────────┘
                     │ HTTP/REST (JSON)
┌────────────────────▼──────────────────────────────────┐
│                                                        │
│   FastAPI V3 Router (/api/v3/*)                       │
│   - Scene CRUD endpoints                              │
│   - Segmentation routes                               │
│   - Removal/inpainting routes                         │
│                                                        │
└────────────────────┬──────────────────────────────────┘
                     │
         ┌───────────┴────────────┬────────────────┐
         │                        │                │
         ▼                        ▼                ▼
    INFERENCE            SCENE STORE         RENDERING
    (ML Models)          (JSON/Neo4j)        (S3/Local)
                         
    SAM2                 scene_*.json        Original
    LaMa                 Immutable           Images
                         EditEvents          Masks
                                             Versions
                                             
         ▼                        ▼                ▼
    GPU (CUDA)           Disk Storage        S3/Cloudflare
    6-18 GB RAM          SQLite Queue        R2 Bucket
```

---

## 🎓 Learning Path

**New to the project?**

1. Read [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md) (15 min)
2. Skim [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md) architecture section (10 min)
3. Run quick start above (5 min)
4. Click on a few objects in the UI
5. Look at specific docs when you hit questions

**Want deep understanding?**

1. Read entire [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md)
2. Study [02_SCHEMA_V3.md](./02_SCHEMA_V3.md) data models
3. Trace code in v3_capstone.py following the diagram
4. Read [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) for ML details
5. Review [06_INTEGRATION_GUIDE_V3.md](./06_INTEGRATION_GUIDE_V3.md) workflows

**Ready to contribute?**

1. Pick a task from progress.md
2. Find relevant sections in documentation
3. Check [08_TESTING_V3.md](./08_TESTING_V3.md) for test patterns
4. Write tests first (TDD)
5. Implement feature
6. Run full test suite

---

## 📞 Support

**Have a question?**

1. Search this README for keywords
2. Check the troubleshooting sections in specific docs
3. Review code comments in source files
4. Check existing tests for usage examples

**Found a bug?**

1. Check [08_TESTING_V3.md](./08_TESTING_V3.md#debugging) debugging section
2. Run test suite: `pytest -v`
3. Enable debug logging in [07_SETUP_V3.md](./07_SETUP_V3.md)
4. File issue with logs

---

## 🔗 Document Map

```
README_V3.md (YOU ARE HERE)
├── 00_SYSTEM_OVERVIEW_V3.md (Start here for concepts)
├── 01_ARCHITECTURE_V3.md (Component design & topology)
├── 02_SCHEMA_V3.md (Data models with examples)
├── 03_API_V3.md (REST endpoints & JSON)
├── 04_ML_PIPELINES_V3.md (SAM2/LaMa algorithms)
├── 05_FRONTEND_V3.md (React components)
├── 06_INTEGRATION_GUIDE_V3.md (Multi-component workflows)
├── 07_SETUP_V3.md (Installation & deployment)
└── 08_TESTING_V3.md (Tests & CI/CD)
```

---

## ✅ Checklist: "Did I Read Enough?"

- [ ] Can I explain what V3 does to someone new? → Read 00_SYSTEM_OVERVIEW_V3.md
- [ ] Can I draw the component architecture? → Read 01_ARCHITECTURE_V3.md
- [ ] Can I look at Pydantic models and understand all fields? → Read 02_SCHEMA_V3.md
- [ ] Can I call each API endpoint and understand the JSON? → Read 03_API_V3.md
- [ ] Can I explain SAM2 segmentation algorithm? → Read 04_ML_PIPELINES_V3.md
- [ ] Can I modify React components? → Read 05_FRONTEND_V3.md
- [ ] Can I trace a user action through all layers? → Read 06_INTEGRATION_GUIDE_V3.md
- [ ] Can I set up a dev environment from scratch? → Read 07_SETUP_V3.md
- [ ] Can I write tests for new features? → Read 08_TESTING_V3.md

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2025 | Initial V3 release, SAM2 + LaMa integration |
| 2.0 | 2024 | Graph-aware editing (superseded) |
| 1.0 | 2023 | Basic image manipulation (archived) |

---

**Last Updated:** 2025  
**Status:** ✅ Production  
**Documentation Coverage:** ~35,000 words across 9 files  

🎉 **Welcome to Capstone V3!**

Start with [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md) or jump to the guide for your role above.
