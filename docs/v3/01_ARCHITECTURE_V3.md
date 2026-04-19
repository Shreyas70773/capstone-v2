# Capstone V3: Detailed Architecture

**Version:** 3.0.0  
**Audience:** Backend Engineers, ML Engineers, Full-Stack Developers  
**Purpose:** Component-level architecture, deployment topology, and integration patterns

---

## 🏛️ Architectural Principles

1. **Graph-Augmented Editing**: Every object and edit is a graph node, not just pixels
2. **Immutable History**: EditEvents form a linked list; no mutations, only new events
3. **Local-First Storage**: JSON files on disk for development; Neo4j optional for analysis
4. **Stateless API**: Each endpoint loads fresh state; no server-side session management
5. **Graceful Degradation**: Mock fallbacks if GPU unavailable; all operations complete
6. **Reproducibility**: Full scene state snapshots enable controlled experimentation

---

## 🔗 Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React + Vite)                             │
│                                                                              │
│  CapstoneStudio.jsx                                                          │
│  ├─ Canvas (fabric.js or p5.js)                                             │
│  ├─ Upload Modal                                                             │
│  ├─ Segment Tools (Point Click, Freehand Lasso)                             │
│  ├─ Edit History Panel                                                       │
│  └─ Settings/Accuracy Presets                                               │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │ HTTP/REST
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐    ┌───────▼──────┐    ┌────▼─────┐
    │ GET /   │    │ POST /       │    │ PUT /    │
    │         │    │              │    │          │
    └─────────┘    └────────────┬─┘    └──────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
   ┌───▼──────────┐      ┌──────▼────────┐      ┌───────▼──────┐
   │ V3_CAPSTONE  │      │ STATIC ASSETS │      │ RENDER       │
   │ ROUTER       │      │               │      │ STORAGE      │
   │              │      │ /public/*     │      │              │
   │ /api/v3/*    │      │ /uploads/*    │      │ put_bytes()  │
   │              │      │               │      │ fetch_image  │
   └───┬──────────┘      └────────────┬──┘      │ _bytes()     │
       │                             │          │              │
       │ Routes to:                  │          └──────┬───────┘
       │                             │                 │
       ├─ /scenes/upload ────────────┼──────────────────→ S3/Local Storage
       │                             │
       ├─ /scenes/{id}              │
       │                             │
       ├─ /scenes/{id}/segment-click─┼─→ INFERENCE LAYER (SAM2 + LaMa)
       │                             │
       ├─ /scenes/{id}/remove-object─┼─→ INFERENCE LAYER (LaMa)
       │                             │
       ├─ /scenes/{id}/history  ────┼─→ SCENE STORE (JSON/Neo4j)
       │                             │
       └─ /capabilities             │
           /accuracy-presets
```

---

## 📊 Layered Architecture

### Layer 1: API Gateway (FastAPI Router)
**File:** `backend/app/routers/v3_capstone.py`

```python
RESPONSIBILITIES:
├─ HTTP Routing (POST, GET, PUT)
├─ Input Validation (Pydantic models)
├─ Error Handling (HTTPException)
├─ Response Serialization (JSON)
└─ Request Logging

KEY ENDPOINTS:
├─ POST /api/v3/scenes/upload
│  ├─ Accept multipart file
│  ├─ Validate image format
│  ├─ Delegate to Scene Store
│  └─ Return scene_id
│
├─ POST /api/v3/scenes/{id}/segment-click
│  ├─ Parse click coordinates (normalized 0-1)
│  ├─ Delegate to Inference Layer
│  ├─ Delegate to Scene Store to register object
│  └─ Return mask + bbox
│
├─ POST /api/v3/scenes/{id}/remove-object
│  ├─ Get inpaint context from Scene Store
│  ├─ Delegate to Inference Layer (LaMa)
│  ├─ Update Scene Document
│  ├─ Record EditEvent
│  └─ Return new canvas image
│
└─ GET /api/v3/capabilities
   └─ Return SAM2/LaMa availability status
```

**Input/Output Example:**
```json
REQUEST: POST /api/v3/scenes/upload
{
  "file": <binary image data>,
  "title": "Living Room Photo",
  "owner_user_id": "user_abc123",
  "email": "user@example.com"
}

RESPONSE: 200 OK
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "canvas_width": 1920,
  "canvas_height": 1080,
  "aspect_ratio": "16:9",
  "image_url": "https://s3.../capstone/originals/scene-upload.png"
}
```

---

### Layer 2: Inference Orchestration
**File:** `backend/app/capstone/inference.py`

Thin wrapper around ML models with:
- Device detection (CUDA vs CPU)
- Error handling and mock fallbacks
- Result post-processing (mask refinement, bbox extraction)

```python
CLASS: SAM2Segmenter
├─ METHODS:
│  ├─ status() → {"ready": bool, "device": str, "model": str}
│  ├─ segment_from_point(image, x, y, tuning) → {"mask_url", "bbox", "area_fraction"}
│  ├─ segment_from_freehand(image, paths, tuning) → {"mask_url", "bbox"}
│  └─ _load_model_once() [lazy loading with lru_cache]
│
└─ ERROR HANDLING:
   ├─ SAM2UnavailableError (if model missing)
   ├─ CUDA OOM → fallback to CPU
   └─ Mock ellipse mask if allow_mock_fallbacks=True

CLASS: LaMaInpainter
├─ METHODS:
│  ├─ status() → {"ready": bool, "device": str, "version": str}
│  ├─ inpaint(image, mask, context_dict, tuning) → inpainted_image
│  └─ inpaint_with_refine(image, mask, refine_config) → high-quality result
│
└─ ERROR HANDLING:
   ├─ LaMaUnavailableError (if model missing)
   ├─ Subprocess timeout → return original image
   └─ CUDA OOM → disable refinement
```

**Example Flow:**
```
1. User clicks (0.5, 0.3) normalized coords
2. API endpoint calls SAM2Segmenter.segment_from_point()
3. Inference layer:
   ├─ Load image from S3/local
   ├─ Denormalize coords: (0.5, 0.3) → (960, 324) pixels
   ├─ Call sam2_predictor.predict(point_coords=..., multimask_output=True)
   ├─ Get mask array (multiple candidates)
   ├─ Select best by SegmentationTuning strategy
   ├─ Refine mask (dilate 0px, erode 0px by default)
   ├─ Compute bbox from mask
   ├─ Save mask to S3/local
   └─ Return mask_url, bbox, area_fraction
```

---

### Layer 3: Scene Persistence
**File:** `backend/app/capstone/store.py`

Manages complete scene state (JSON-first, Neo4j-optional):

```python
CLASS: CapstoneSceneStore
├─ ROOT: backend/uploads/capstone/scenes/
│
├─ METHODS:
│  ├─ create_scene(req: CreateSceneRequest) → SceneDocument
│  │  ├─ Generate scene_id
│  │  ├─ Initialize empty objects[], text_regions[], edit_events[]
│  │  ├─ Save to JSON
│  │  ├─ (Optional) Sync to Neo4j
│  │  └─ Return SceneDocument
│  │
│  ├─ get_scene(scene_id) → SceneDocument
│  │  ├─ Load from JSON (primary)
│  │  └─ Fallback to Neo4j if JSON missing
│  │
│  ├─ add_object(scene_id, req) → SceneDocument
│  │  ├─ Load current document
│  │  ├─ Append new ImageObjectNode
│  │  ├─ Recompute spatial relationships
│  │  ├─ Write to JSON + Neo4j
│  │  └─ Return updated document
│  │
│  ├─ record_edit(scene_id, req) → EditEventNode
│  │  ├─ Create new CanvasVersionNode
│  │  ├─ Create EditEventNode with before/after snapshots
│  │  ├─ Link to previous event
│  │  ├─ Write to JSON + Neo4j
│  │  └─ Return event record
│  │
│  └─ get_inpaint_context(scene_id, object_id) → dict
│     ├─ Find object by ID
│     ├─ Query spatial_relationships (neighbors)
│     ├─ Query text_regions (what to preserve)
│     └─ Return context for inpainting
│
└─ SPATIAL RELATIONSHIP COMPUTATION:
   ├─ For each pair of objects:
   │  ├─ Compute bbox overlap (contains, overlaps)
   │  ├─ Compute directional relationship (above, left_of, etc)
   │  ├─ Compute distance (center-to-center pixels)
   │  └─ Create SpatialRelationshipNode
   │
   └─ Run after EVERY state change (add_object, remove_object, etc)
```

**Persistence Format (JSON):**
```json
{
  "user": {
    "user_id": "local-user",
    "email": null,
    "storage_quota_mb": 2048,
    "created_at": "2026-04-18T12:34:56Z",
    "updated_at": "2026-04-18T12:34:56Z",
    "schema_version": "3.0.0"
  },
  "scene": {
    "scene_id": "scene_a1b2c3d4e5f6",
    "image_path": "https://s3.../capstone/originals/scene-upload.png",
    "canvas_width": 1920,
    "canvas_height": 1080,
    "aspect_ratio": "16:9",
    "owner_user_id": "local-user",
    "title": "Living Room Photo",
    "created_at": "2026-04-18T12:34:56Z",
    "updated_at": "2026-04-18T12:34:56Z",
    "schema_version": "3.0.0"
  },
  "objects": [
    {
      "object_id": "obj_1a2b3c4d5e6f",
      "class_label": "chair",
      "confidence": 1.0,
      "bbox": {"x": 100, "y": 200, "w": 300, "h": 400},
      "mask_path": "https://s3.../capstone/masks/chair-mask.png",
      "z_order": 0,
      "is_locked": false,
      "is_text": false,
      "metadata": {},
      "created_at": "2026-04-18T12:35:00Z",
      "updated_at": "2026-04-18T12:35:00Z",
      "schema_version": "3.0.0"
    }
  ],
  "text_regions": [],
  "spatial_relationships": [
    {
      "rel_id": "rel_x1y2z3",
      "source_object_id": "obj_1a2b3c4d5e6f",
      "target_object_id": "obj_7g8h9i0j1k2l",
      "predicate": "left_of",
      "confidence": 0.95,
      "distance_px": 150.0,
      "created_at": "2026-04-18T12:35:00Z",
      "updated_at": "2026-04-18T12:35:00Z",
      "schema_version": "3.0.0"
    }
  ],
  "edit_events": [
    {
      "event_id": "edit_m1n2o3p4q5r6",
      "event_type": "INIT",
      "delta_json": {},
      "before_state_json": {},
      "after_state_json": { "scene": {...}, "objects": [] },
      "user_id": "local-user",
      "affected_object_ids": [],
      "prev_event_id": null,
      "canvas_version_id": "ver_s1t2u3v4w5x6",
      "created_at": "2026-04-18T12:34:56Z",
      "updated_at": "2026-04-18T12:34:56Z",
      "schema_version": "3.0.0"
    },
    {
      "event_id": "edit_s7t8u9v0w1x2",
      "event_type": "REMOVE_OBJECT",
      "delta_json": {
        "removed_object_id": "obj_1a2b3c4d5e6f",
        "mask_area_px": 120000,
        "inpaint_context": "chair on left, painting above"
      },
      "before_state_json": { "objects": [{...chair...}] },
      "after_state_json": { "objects": [] },
      "user_id": "local-user",
      "affected_object_ids": ["obj_1a2b3c4d5e6f"],
      "prev_event_id": "edit_m1n2o3p4q5r6",
      "canvas_version_id": "ver_y3z4a5b6c7d8",
      "created_at": "2026-04-18T12:36:00Z",
      "updated_at": "2026-04-18T12:36:00Z",
      "schema_version": "3.0.0"
    }
  ],
  "canvas_versions": [
    {
      "version_id": "ver_s1t2u3v4w5x6",
      "composite_image_path": "https://s3.../capstone/originals/scene-upload.png",
      "graph_snapshot_json": { "objects": [] },
      "is_current": false,
      "created_at": "2026-04-18T12:34:56Z",
      "updated_at": "2026-04-18T12:34:56Z",
      "schema_version": "3.0.0"
    },
    {
      "version_id": "ver_y3z4a5b6c7d8",
      "composite_image_path": "https://s3.../capstone/canvas_versions/scene_a1b2c3d4e5f6_v2.png",
      "graph_snapshot_json": { "objects": [] },
      "is_current": true,
      "created_at": "2026-04-18T12:36:00Z",
      "updated_at": "2026-04-18T12:36:00Z",
      "schema_version": "3.0.0"
    }
  ]
}
```

---

### Layer 4: Database (Neo4j)
**File:** `backend/app/database/capstone_schema_v3.cypher`

Optional graph queries for spatial analysis:

```cypher
-- Constraints (enforced uniqueness)
CREATE CONSTRAINT capstone_scene_id IF NOT EXISTS
FOR (s:CapstoneScene) REQUIRE s.scene_id IS UNIQUE;

CREATE CONSTRAINT capstone_object_id IF NOT EXISTS
FOR (o:CapstoneImageObject) REQUIRE o.object_id IS UNIQUE;

-- Example Query: Find all neighbors of an object
MATCH (scene:CapstoneScene {scene_id: $scene_id})
      -[:CONTAINS]-> (obj:CapstoneImageObject {object_id: $object_id})
      -[rel:SPATIAL_RELATIONSHIP]-> (neighbor:CapstoneImageObject)
RETURN neighbor, rel;

-- Example Query: Full edit history
MATCH (scene:CapstoneScene {scene_id: $scene_id})
      -[:HAS_EVENT]-> (event:CapstoneEditEvent)
RETURN event
ORDER BY event.created_at DESC;
```

**Role in V3:**
- Primary storage: JSON files (faster, offline-capable)
- Secondary storage: Neo4j (graph queries, relationship visualization)
- Not required for basic functionality; optional for advanced analytics

---

### Layer 5: ML Model Runtime
**File:** `backend/app/capstone/runtime.py`

Configuration and device management:

```python
CLASS: CapstoneRuntimeSettings
├─ SAM2 Configuration:
│  ├─ sam2_checkpoint: Path to .pt file (2.6 GB)
│  ├─ sam2_config: YAML config (configs/sam2.1/sam2.1_hiera_l.yaml)
│  ├─ device_preference: "auto" | "cuda" | "cpu"
│  └─ allow_mock_fallbacks: bool (for testing without GPU)
│
├─ LaMa Configuration:
│  ├─ lama_repo_path: Git clone of LaMa repository
│  ├─ lama_model_path: Path to big-lama checkpoint (4.3 GB)
│  ├─ lama_python_executable: Python interpreter for subprocess
│  ├─ lama_refiner_*: Refinement hyperparameters
│  └─ lama_retry_cpu_on_cuda_failure: bool
│
└─ DEVICE RESOLUTION LOGIC:
   ├─ If preference == "cuda":
   │  ├─ Check torch.cuda.is_available()
   │  └─ Use "cuda" if available, else "cpu"
   │
   └─ If preference == "auto":
      ├─ Check torch availability
      ├─ Check CUDA availability
      └─ Default to "cpu"

FUNCTIONS:
├─ has_sam2() → bool (check if sam2 module installed)
├─ has_torch() → bool (check if torch installed)
├─ resolve_device(preference) → "cuda" | "cpu"
└─ get_capstone_runtime_settings() → CapstoneRuntimeSettings (cached, lazy-loaded)
```

**Environment Variables (backend/.env):**
```bash
# SAM2
CAPSTONE_SAM2_CHECKPOINT=checkpoints/sam2.1_hiera_large.pt
CAPSTONE_SAM2_CONFIG=configs/sam2.1/sam2.1_hiera_l.yaml

# LaMa
CAPSTONE_LAMA_REPO_PATH=external/lama
CAPSTONE_LAMA_MODEL_PATH=models/big-lama
CAPSTONE_LAMA_PYTHON=python
CAPSTONE_LAMA_REFINER_GPU_IDS=0,
CAPSTONE_LAMA_ALLOW_WINDOWS_REFINE=false

# General
CAPSTONE_DEVICE=auto
CAPSTONE_ALLOW_MOCK_FALLBACKS=false
```

---

## 🗄️ Storage Architecture

### Filesystem Layout
```
backend/
├─ checkpoints/
│  └─ sam2.1_hiera_large.pt          (2.6 GB) [Checked in or downloaded]
│
├─ models/
│  └─ big-lama/                      (4.3 GB) [Downloaded at setup]
│     ├─ config.yaml
│     ├─ checkpoint.pt
│     └─ readme.md
│
├─ uploads/
│  └─ capstone/
│     ├─ originals/                  [Original user uploads]
│     │  └─ scene-upload-abc123.png
│     ├─ masks/                      [SAM2-generated masks]
│     │  └─ chair-mask-def456.png
│     ├─ canvas_versions/            [Composite images after inpainting]
│     │  └─ scene_abc123_v2.png
│     └─ scenes/                     [JSON scene documents]
│        └─ scene_abc123.json
│
└─ external/
   └─ lama/                          [LaMa git clone + models]
      ├─ bin/
      ├─ lama/
      ├─ tests/
      └─ models/ [Big-LaMa weights]
```

### S3/Cloudflare R2 Storage (Optional)
```
s3://capstone-storage/
├─ capstone/originals/               [Original uploads]
├─ capstone/masks/                   [Segmentation masks]
├─ capstone/canvas_versions/         [Inpainted composites]
└─ capstone/scenes/                  [JSON backups]
```

**Storage Strategy:**
- Local: Fast, offline-capable; ideal for development
- S3: Persistent, shareable URLs; ideal for production

---

## 🔄 Deployment Topology

### Development (Single Machine)
```
┌──────────────────────────────────────────┐
│      Developer Laptop (macOS/Windows)    │
├──────────────────────────────────────────┤
│                                          │
│  Frontend Dev Server (Vite)              │
│  http://localhost:5173                   │
│                                          │
│  Backend Dev Server (FastAPI)            │
│  http://localhost:8000                   │
│                                          │
│  Local Storage (/uploads/capstone/)      │
│  Local Neo4j (optional, bolt://...)      │
│  GPU (NVIDIA if available)               │
│                                          │
└──────────────────────────────────────────┘
```

### Production (Cloud Deployment)
```
┌─────────────────────────────────────────────────────────────────┐
│                      Internet                                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  CDN + Reverse Proxy│
        │  (Cloudflare Pages) │
        └──────────┬──────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼──────┐      ┌───────▼──────┐
   │ Frontend   │      │ Backend      │
   │ (Vercel)   │      │ (Railway)    │
   │            │      │              │
   │ Vite Build │      │ FastAPI + ML │
   │ React      │      │ PyTorch/CUDA │
   │ HTML/JS/CSS│      │              │
   └────────────┘      └───────┬──────┘
                                │
                    ┌───────────┼──────────┐
                    │           │          │
              ┌─────▼──┐  ┌─────▼──┐  ┌──▼────┐
              │   S3   │  │ Neo4j  │  │Cache  │
              │ (R2)   │  │Aura    │  │Redis  │
              └────────┘  └────────┘  └───────┘
```

---

## 📈 Performance Characteristics

| Operation | Latency | Memory | Notes |
|-----------|---------|--------|-------|
| Image upload | 500ms | 50MB | Depends on image size |
| SAM2 segmentation (point) | 2-3s | 6GB VRAM | First call slower (model load) |
| Mask refinement | 100-500ms | 100MB | Dilate/erode operations |
| LaMa inpainting | 5-10s | 8-12GB VRAM | Depends on mask size |
| LaMa refinement | +2-5s | +4GB VRAM | Optional, improves quality |
| Scene document save | 100ms | 50MB | JSON serialization |
| Spatial relationship compute | 50-200ms | 100MB | O(n²) for n objects |

**Optimization Strategies:**
1. Batch segmentation requests (if multiple objects)
2. Cache model weights in memory (done via lru_cache)
3. Async inpainting (don't block API during inference)
4. Progressive mask refinement (dilate/erode in GPU if possible)

---

## 🚨 Error Handling & Fallbacks

```
SCENARIO 1: GPU Out of Memory (OOM)
├─ SAM2 OOM → Fallback to CPU (slower but works)
├─ LaMa OOM → Disable refinement (basic inpainting still works)
└─ Both OOM → Return mock/error response

SCENARIO 2: Model Not Installed
├─ SAM2 missing → SAM2UnavailableError
│  ├─ If allow_mock_fallbacks=True → Return mock ellipse mask
│  └─ Else → Return 503 Service Unavailable
├─ LaMa missing → LaMaUnavailableError
│  ├─ If allow_mock_fallbacks=True → Return original image unchanged
│  └─ Else → Return 503 Service Unavailable

SCENARIO 3: Invalid Input
├─ Empty image → HTTPException 400
├─ Click outside canvas → Clamp to bounds
├─ Non-positive dimensions → HTTPException 400

SCENARIO 4: Network Issues
├─ S3 upload timeout → Retry with exponential backoff
├─ Neo4j connection lost → Continue with JSON-only storage
└─ Frontend connection lost → Frontend shows offline mode
```

---

## 🔐 Security Considerations

1. **Input Validation**
   - All coordinates validated as floats 0.0-1.0
   - All text inputs sanitized (no script injection)
   - File uploads validated as image MIME types

2. **File Access**
   - All files stored in sandboxed `backend/uploads/` directory
   - No path traversal via user input (scene_id is UUID-like)
   - S3 permissions managed via IAM roles (production)

3. **API Authentication** (not yet implemented)
   - Current: No auth (local development)
   - TODO: JWT token validation for production

4. **GPU Resource Limits**
   - Set CUDA device limits to prevent runaway processes
   - Timeout long-running inferences (>30s)
   - Queue requests if GPU busy (not yet implemented)

---

## 📊 Monitoring & Observability

**Metrics to Track:**
```
├─ /api/v3/scenes/upload
│  ├─ Upload latency (p50, p95, p99)
│  ├─ File size distribution
│  └─ Error rate
│
├─ /api/v3/scenes/{id}/segment-click
│  ├─ Segmentation latency (p50, p95, p99)
│  ├─ SAM2 model load time (first call)
│  ├─ CPU vs GPU usage
│  └─ OOM events
│
├─ /api/v3/scenes/{id}/remove-object
│  ├─ Inpainting latency (p50, p95, p99)
│  ├─ LaMa with/without refinement
│  ├─ GPU memory peak usage
│  └─ Timeout count
│
└─ General
   ├─ Total scenes created
   ├─ Total objects segmented
   ├─ Total edits recorded
   └─ Neo4j query latency (if enabled)
```

**Logging Strategy:**
- FastAPI built-in logging (configured in `run_server.py`)
- Model inference logging in `inference.py`
- Scene state changes logged in `store.py`

---

## 🧪 Testing Strategy (See [08_TESTING_V3.md](./08_TESTING_V3.md) for Details)

| Test Type | Coverage | Tools |
|-----------|----------|-------|
| Unit Tests | Models, inference, store | pytest |
| Integration Tests | API + store + inference | pytest + requests |
| E2E Tests | Full user flow | Playwright or Selenium |
| Performance Tests | Latency benchmarks | locust, pytest-benchmark |
| ML Validation | SAM2/LaMa outputs | Custom image validators |

---

## 📝 Summary

**V3 Architecture** prioritizes:
1. **Clarity**: Each layer has a single responsibility
2. **Extensibility**: Easy to add new ML models or storage backends
3. **Reproducibility**: Full state snapshots enable experimentation
4. **Resilience**: Graceful fallbacks if GPU unavailable

**Next:** Read [02_SCHEMA_V3.md](./02_SCHEMA_V3.md) for detailed data model documentation.
