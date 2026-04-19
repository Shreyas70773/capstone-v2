# Capstone V3: Integration Guide

**Version:** 3.0.0  
**Audience:** Architects, Full-Stack Developers  
**Purpose:** System integration patterns and deployment topology

---

## 🔗 Multi-Component Integration

### System Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                    USER (Web Browser)                              │
│                  http://localhost:5173                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP/WebSocket
                ┌────────────┴─────────────┐
                │                          │
        ┌───────▼──────────┐      ┌────────▼─────────┐
        │  REACT FRONTEND  │      │  STATIC ASSETS   │
        │  (Vite Dev)      │      │  CSS/JS/Images   │
        │                  │      │                  │
        │ CapstoneStudio   │      │ /public/*        │
        │ Components       │      │ /dist/*          │
        └───────┬──────────┘      └──────────────────┘
                │ HTTP REST (JSON)
        ┌───────▼──────────────────────────────┐
        │   FASTAPI BACKEND                    │
        │   http://localhost:8000              │
        │                                      │
        │ ┌─────────────────────────────────┐ │
        │ │ V3_CAPSTONE ROUTER              │ │
        │ │ /api/v3/*                       │ │
        │ └────────┬────────────────────────┘ │
        │          │                          │
        │ ┌────────▼─────────┬─────────┬─────▼──────┐
        │ │                  │         │            │
        │ ▼                  ▼         ▼            ▼
        │ INFERENCE    SCENE STORE   RENDERING   DATABASE
        │ LAYER        (JSON/Neo4j)  STORAGE     (Neo4j)
        │                                        
        │ SAM2          JSON files   S3/Local    Constraints
        │ LaMa          scene_*.json S3/R2       Relationships
        │               immutable    Objects
        └───────────────────────────────────────────┘
                │               │         │
                ▼               ▼         ▼
        ┌───────────────┐ ┌─────────┐ ┌──────────┐
        │ GPU (CUDA)    │ │ Disk    │ │ Neo4j    │
        │ 6-18 GB VRAM  │ │ Storage │ │ Aura     │
        │               │ │ (uploads)│ │ (optional)
        └───────────────┘ └─────────┘ └──────────┘
```

---

## 🔄 Request-Response Cycle (Detailed)

### Workflow: Click to Segment → Remove Object

```
USER ACTION: Click canvas at (0.5, 0.3)
│
▼
┌─ FRONTEND ─────────────────────────────────────────────┐
│ CapstoneStudio.jsx:handleCanvasClick(x, y)             │
│ ├─ normalize coords (already 0-1)                      │
│ └─ POST /api/v3/scenes/{id}/segment-click              │
│    ├─ click_x: 0.5                                     │
│    ├─ click_y: 0.3                                     │
│    ├─ label: "sofa"                                    │
│    └─ tuning: SegmentationTuning()                     │
└────────────────────┬──────────────────────────────────┘
                     │ HTTP POST (JSON)
┌────────────────────▼──────────────────────────────────┐
│ BACKEND: FastAPI Route Handler                        │
│ v3_capstone.py:segment_click()                        │
│                                                        │
│ 1. Validate input (Pydantic)                          │
│ 2. Load scene from disk                               │
│ 3. Call Inference Layer                               │
└────────────────────┬──────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────┐
│ INFERENCE LAYER: inference.py                         │
│ SAM2Segmenter.segment_from_point()                    │
│                                                        │
│ 1. Load image from S3/local                           │
│ 2. Denormalize click: (0.5, 0.3) → (960, 324) px     │
│ 3. Load SAM2 model (once, cached)                     │
│ 4. Call sam2_predictor.predict()                      │
│ 5. Select best mask by tuning strategy                │
│ 6. Refine mask (dilate/erode)                         │
│ 7. Compute bbox from mask                             │
│ 8. Save mask to S3                                    │
│ 9. Return mask_url, bbox, confidence                  │
└────────────────────┬──────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────┐
│ SCENE STORE: store.py                                 │
│ capstone_scene_store.add_object()                     │
│                                                        │
│ 1. Get current scene from JSON                        │
│ 2. Create new ImageObjectNode                         │
│ 3. Append to scene.objects                            │
│ 4. Recompute spatial_relationships                    │
│ 5. Update timestamps                                  │
│ 6. Write to JSON (atomic)                             │
│ 7. (Optional) Sync to Neo4j                           │
└────────────────────┬──────────────────────────────────┘
                     │ Return response
┌────────────────────▼──────────────────────────────────┐
│ API RESPONSE (200 OK)                                 │
│ {                                                      │
│   "object_id": "obj_abc123",                          │
│   "mask_url": "https://s3.../masks/sofa_abc.png",    │
│   "bbox": {"x": 850, "y": 200, "w": 220, "h": 248}  │
│ }                                                      │
└────────────────────┬──────────────────────────────────┘
                     │ HTTP 200 (JSON)
┌────────────────────▼──────────────────────────────────┐
│ FRONTEND: Handle response                             │
│ handleCanvasClick() completion                        │
│                                                        │
│ 1. Store object_id in state                           │
│ 2. Add mask to segmentationMasks map                  │
│ 3. Show mask overlay on canvas                        │
│ 4. Refresh scene state via GET /api/v3/scenes/{id}   │
│ 5. Render new scene.objects list                      │
└────────────────────┬──────────────────────────────────┘
                     │
USER SEES: Segmentation mask overlay on sofa
           Remove Object button appears
           
═══════════════════════════════════════════════════════

USER ACTION: Click "Remove Object" button
│
▼
┌─ FRONTEND: handleRemoveObject(object_id) ──────────────┐
│ POST /api/v3/scenes/{id}/remove-object                 │
│ ├─ object_id: "obj_abc123"                             │
│ ├─ record_event: true                                  │
│ └─ tuning: InpaintTuning(mask_dilate_px=4)            │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP POST
┌────────────────────▼─────────────────────────────────┐
│ BACKEND: v3_capstone.py:remove_object()              │
│                                                      │
│ 1. Load scene from JSON                              │
│ 2. Find object by ID                                 │
│ 3. Get inpaint context (neighbors, text regions)     │
│ 4. Call Inference Layer (LaMa)                       │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│ INFERENCE: LaMaInpainter.inpaint()                   │
│                                                      │
│ 1. Load image from S3                                │
│ 2. Load mask from S3                                 │
│ 3. Dilate mask by 4px (tuning)                       │
│ 4. Build context prompt from neighbors               │
│ 5. Call LaMa subprocess                              │
│ 6. Wait 5-10s for result (GPU)                       │
│ 7. Save inpainted image to S3                        │
│ 8. Return new image URL                              │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│ SCENE STORE: record_edit()                           │
│                                                      │
│ 1. Get current scene                                 │
│ 2. Create CanvasVersionNode (new composite image)    │
│ 3. Create EditEventNode:                             │
│    ├─ event_type: "REMOVE_OBJECT"                    │
│    ├─ delta_json: {removed_object_id, ...}           │
│    ├─ before_state_json: {...scene before...}        │
│    ├─ after_state_json: {...scene after...}          │
│    └─ canvas_version_id: link to new image           │
│ 4. Remove object from scene.objects                  │
│ 5. Recompute spatial_relationships                   │
│ 6. Atomic write to JSON                              │
│ 7. Sync to Neo4j                                     │
└────────────────────┬─────────────────────────────────┘
                     │ Return response
┌────────────────────▼─────────────────────────────────┐
│ API RESPONSE (200 OK)                                │
│ {                                                    │
│   "new_canvas_image_url": "https://s3.../v2.png",  │
│   "edit_event_id": "edit_removal_123",              │
│   "inpaint_time_ms": 7234                           │
│ }                                                    │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP 200 (JSON)
┌────────────────────▼─────────────────────────────────┐
│ FRONTEND: Complete                                   │
│                                                      │
│ 1. Update canvas with new image URL                 │
│ 2. Clear mask overlay                                │
│ 3. Deselect object                                   │
│ 4. Refresh scene state                               │
│ 5. User sees: Updated canvas, object removed         │
└────────────────────────────────────────────────────────┘

USER SEES: Inpainted canvas with object removed
           Object no longer appears in objects list
```

---

## 🗄️ Storage Integration

### JSON File Storage (Primary)

```python
# All scene state stored in single JSON file
backend/uploads/capstone/scenes/scene_a1b2c3d4e5f6.json

# File structure:
{
  "user": {...},              # UserNode
  "scene": {...},             # SceneNode
  "objects": [...],           # List of ImageObjectNode
  "text_regions": [...],      # List of TextRegionNode
  "spatial_relationships": [...],  # List of SpatialRelationshipNode
  "edit_events": [...],       # Immutable edit history
  "canvas_versions": [...]    # Image snapshots
}

# Atomic writes ensure consistency:
# 1. Write to temporary file
# 2. Verify JSON validity
# 3. Rename to final location
# (No corruption if process crashes mid-write)
```

### S3/Cloudflare R2 Integration

```python
# Image URLs structure
https://s3.example.com/capstone/originals/scene-upload-xyz.png    # User uploads
https://s3.example.com/capstone/masks/sofa-mask-abc.png           # SAM2 masks
https://s3.example.com/capstone/canvas_versions/scene_xyz_v2.png  # Inpainted

# Implementation in storage.py:
def put_bytes(prefix: str, filename: str, data: bytes, mime: str) -> str:
    """Upload to S3 and return signed URL."""
    if USE_S3:
        # Upload to Cloudflare R2 / AWS S3
        s3_client.put_object(
            Bucket="capstone-storage",
            Key=f"{prefix}/{filename}",
            Body=data,
            ContentType=mime
        )
        return f"https://s3.example.com/{prefix}/{filename}"
    else:
        # Fall back to local storage
        path = Path("uploads") / prefix / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"http://localhost:8000/uploads/{prefix}/{filename}"

def fetch_image_bytes(url: str) -> bytes:
    """Download image from URL (S3 or local)."""
    response = requests.get(url)
    return response.content
```

### Neo4j Graph Sync (Optional)

```python
# Scene state is PRIMARY in JSON
# Neo4j is SECONDARY for queries

def _sync_to_neo4j(doc: SceneDocument):
    """Sync JSON document to Neo4j."""
    query = """
    MERGE (scene:CapstoneScene {scene_id: $scene_id})
    SET scene += $scene_props
    
    WITH scene
    UNWIND $objects AS obj
    MERGE (object:CapstoneImageObject {object_id: obj.object_id})
    SET object += obj
    MERGE (scene)-[:CONTAINS]->(object)
    
    WITH scene
    UNWIND $edit_events AS event
    CREATE (e:CapstoneEditEvent)
    SET e = event
    MERGE (scene)-[:HAS_EVENT]->(e)
    """
    
    neo4j_client.run(query, {
        "scene_id": doc.scene.scene_id,
        "scene_props": doc.scene.model_dump(),
        "objects": [o.model_dump() for o in doc.objects],
        "edit_events": [e.model_dump() for e in doc.edit_events]
    })
```

---

## 🔐 Error Handling & Recovery

### Cascading Fallbacks

```python
# When SAM2 unavailable:
1. Try GPU SAM2
2. Fall back to CPU SAM2 (slower)
3. If SAM2UnavailableError, check allow_mock_fallbacks
4. If True, return mock ellipse mask
5. If False, return 503 Service Unavailable

# When LaMa unavailable:
1. Try GPU LaMa
2. Fall back to CPU LaMa (slower)
3. If timeout (>30s), return original image
4. If LaMaUnavailableError, check allow_mock_fallbacks
5. If True, return original image (no inpainting)
6. If False, return 503 Service Unavailable

# When S3 unavailable:
1. Try S3 upload
2. Fall back to local storage
3. Return local file:// URL
4. (Frontend can still access via relative URL)

# When Neo4j unavailable:
1. Try Neo4j sync
2. Log warning but continue (JSON is primary)
3. Don't fail the entire operation
```

### Scene State Recovery

```python
# If JSON corruption detected during load:
1. Try loading from backup (if exists)
2. Try reconstructing from neo4j (if enabled)
3. Return empty scene (safest fallback)

# Edit event immutability ensures:
- Can always reconstruct exact scene state at any point in history
- No data loss from partial edits
- Can replay all events for debugging
```

---

## 📊 Monitoring & Observability

### Metrics Collection Points

```python
# In inference.py:
import time

def segment_from_point(self, ...):
    start = time.time()
    
    result = self._predictor.predict(...)
    
    latency_ms = (time.time() - start) * 1000
    logger.info(f"SAM2 segmentation took {latency_ms:.1f}ms")
    
    return result

# In store.py:
def record_edit(self, scene_id, req):
    start = time.time()
    
    # ... processing ...
    
    latency_ms = (time.time() - start) * 1000
    logger.info(f"Edit recorded in {latency_ms:.1f}ms")
    
    return event

# In v3_capstone.py:
@router.post("/scenes/{scene_id}/remove-object")
async def remove_object(scene_id: str, req: RemoveObjectRequest):
    logger.info(f"Remove object request for {scene_id}")
    
    try:
        result = await inference_layer.inpaint(...)
        logger.info(f"Inpainting completed: {result.inpaint_time_ms}ms")
        return result
    except Exception as e:
        logger.error(f"Removal failed: {e}", exc_info=True)
        raise
```

### Logging Strategy

```python
# Structured logging with context
import logging
from pythonjsonlogger import jsonlogger

handler = logging.FileHandler("capstone_v3.log")
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

# Usage:
logger.info("Object segmented", extra={
    "scene_id": scene_id,
    "object_id": object_id,
    "method": "SAM2",
    "confidence": 0.98,
    "latency_ms": 1234
})
```

---

## 🚀 Deployment Checklist

**Before Production:**

```
┌─────────────────────────────────────────┐
│ Code Quality                            │
├─────────────────────────────────────────┤
☐ All tests pass (pytest + npm test)
☐ Coverage >= 80% (backend), >= 70% (frontend)
☐ No critical security issues (bandit, snyk)
☐ Code review completed
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Performance                             │
├─────────────────────────────────────────┤
☐ SAM2 latency < 2s (cached)
☐ LaMa latency < 10s
☐ API response time < 500ms (excluding ML)
☐ Frontend bundle < 500KB gzipped
☐ No memory leaks (profiled)
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Configuration                           │
├─────────────────────────────────────────┤
☐ Models downloaded and checksummed
☐ S3 credentials configured
☐ Neo4j connection tested
☐ CORS headers correct
☐ Rate limiting enabled (if applicable)
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Monitoring                              │
├─────────────────────────────────────────┤
☐ Logging configured (file + remote)
☐ Error tracking enabled (Sentry, etc)
☐ Metrics collection active
☐ Alerts configured (downtime, errors)
☐ Health checks set up
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Documentation                           │
├─────────────────────────────────────────┤
☐ API docs generated (FastAPI /docs)
☐ Deployment runbook completed
☐ Incident response plan written
☐ Capacity plan reviewed
└─────────────────────────────────────────┘
```

---

## 📈 Scaling Considerations (Future)

**Multi-User:**
- Add user authentication (JWT)
- Per-user storage quotas
- Queue management for ML inference
- GPU time allocation

**High Throughput:**
- GPU batching (multiple segmentations)
- LaMa subprocess pool (N workers)
- Redis caching for repeated requests
- Horizontal scaling (K8s pods)

**Distributed:**
- Scene lock mechanism (concurrent edits)
- Event sourcing for audit trail
- CRDT for eventual consistency
- Distributed transaction log

---

**Next:** Proceed to [README_V3.md](./README_V3.md) for quick reference.
