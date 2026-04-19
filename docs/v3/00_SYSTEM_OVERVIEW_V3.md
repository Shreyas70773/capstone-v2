# Capstone V3: System Overview

**Version:** 3.0.0  
**Last Updated:** April 2026  
**Status:** Production Implementation  
**Project Type:** Academic Capstone - Graph-Augmented Image Manipulation System

---

## 🎯 Executive Summary

**V3 transforms the capstone project from a brand-aligned content generator into a persistent scene-graph image manipulation system.** Every object, text region, and edit operation is explicitly represented in a graph database, enabling context-aware inpainting, spatial reasoning, and measurable evaluation.

### Core Thesis

Traditional image editing is pixel-focused and stateless. V3 implements **graph-augmented editing** where:
- Each image object is a first-class graph node with provenance
- Every edit creates an immutable `EditEvent` in the graph
- Inpainting operations query spatial context (neighboring objects, text regions)
- This enables rigorous evaluation: blind inpainting vs. graph-guided inpainting on identical scenes

### Key Innovation

**Graph-Aware Object Removal:**
1. User clicks to segment an object (SAM 2)
2. Backend queries Neo4j for neighboring objects and text regions
3. Inpainting model (LaMa) receives context about what should be preserved
4. Spatial relationships automatically recomputed after edit
5. Full state recorded as `EditEvent` for reproducibility

---

## 📊 System Architecture at a Glance

```
┌───────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                              │
│                   (React Frontend - Vite)                          │
│                                                                    │
│         Canvas Editor | Upload | Tools | History Panel            │
└─────────────────────────────────────────────────────────────────┬─┘
                                 │ HTTP
                    ┌────────────┴─────────────┐
                    │                          │
           ┌────────▼──────────┐      ┌────────▼──────────┐
           │   FastAPI Router  │      │   Static Assets   │
           │  `/api/v3/...`    │      │   (Images, etc)   │
           └────────┬──────────┘      └───────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼──┐  ┌─────▼──────┐  ┌▼────────────┐
    │ SAM2 │  │ LaMa       │  │ Graph Store │
    │      │  │ Inpainter  │  │  (Neo4j)    │
    │Segm  │  │            │  │             │
    │enttn │  │ Big-LaMa   │  │ Nodes:      │
    │      │  │ (GPU-opt)  │  │ - Scene     │
    └──────┘  └────────────┘  │ - Object    │
                              │ - Text      │
                              │ - Edit      │
                              │ - Spatial   │
                              └─────────────┘
        
        Local Storage Layer
        ├─ Scene JSON files (.json)
        ├─ Object masks (.png)
        ├─ Canvas versions (.png)
        └─ Image cache
```

---

## 🔄 Data Flow: Complete Journey

### Scenario: User Removes an Object from a Photo

```
STEP 1: UPLOAD IMAGE
─────────────────────
Browser: User selects image file
  ↓
API: POST /api/v3/scenes/upload
  ├─ Save RGB image to storage (S3/local)
  ├─ Create SceneNode with image_path, canvas dimensions
  ├─ Initialize empty objects[], text_regions[], edit_events[]
  ├─ Save SceneDocument to JSON + Neo4j
  └─ Return scene_id to frontend

Frontend: Display image in canvas, ready for editing


STEP 2: CLICK TO SEGMENT OBJECT
────────────────────────────────
Browser: User clicks on object in canvas (x, y) normalized [0, 1]
  ↓
API: POST /api/v3/scenes/{scene_id}/segment-click
  ├─ Load image from image_path
  ├─ Denormalize click coords to pixel space
  ├─ Call SAM2.predict_from_point(image, coords) → mask
  ├─ Refine mask based on SegmentationTuning (dilate/erode)
  ├─ Compute bounding box from mask
  ├─ Create ImageObjectNode with mask_url, bbox, class_label
  ├─ Append to scene.objects
  ├─ Recompute spatial relationships (overlaps, adjacency, etc)
  ├─ Save updated SceneDocument
  └─ Return ImageObjectNode with mask visualization

Frontend: Show mask overlay, confirm or reject segmentation


STEP 3: REQUEST OBJECT REMOVAL
───────────────────────────────
Browser: User clicks "Remove Object" button
  ↓
API: POST /api/v3/scenes/{scene_id}/remove-object
  ├─ Load current SceneDocument
  ├─ Locate object_id in scene.objects
  ├─ Get inpaint context:
  │  ├─ Query spatial_relationships (neighboring objects)
  │  ├─ Query text_regions overlapping area
  │  ├─ Build textual context ("preserve logos to the left")
  │  └─ Return context to inpainter
  ├─ Call LaMa with:
  │  ├─ image (original pixels)
  │  ├─ mask (object to remove)
  │  ├─ context dict (spatial neighbors, text)
  │  ├─ InpaintTuning (dilate mask 4px, preserve text regions)
  │  └─ GPU allocation + refinement budget
  ├─ Get inpainted image back from LaMa
  ├─ Create CanvasVersionNode (composite image)
  ├─ Remove object from scene.objects
  ├─ Recompute spatial relationships
  ├─ Create EditEventNode:
  │  ├─ event_type: "REMOVE_OBJECT"
  │  ├─ before_state_json: full scene state before
  │  ├─ after_state_json: full scene state after
  │  ├─ delta_json: {"removed_object_id": "...", "mask_area_px": ...}
  │  ├─ affected_object_ids: [neighbors that may have relationship changes]
  │  └─ canvas_version_id: link to new composite image
  ├─ Append event to scene.edit_events
  ├─ Write updated scene to JSON + Neo4j
  └─ Return new composite image URL + canvas_version_id

Frontend: Show inpainted result, enable undo/redo


STEP 4: QUERY HISTORY
──────────────────────
Browser: User opens "Edit History" panel
  ↓
API: GET /api/v3/scenes/{scene_id}/history
  ├─ Load scene.edit_events (all EditEventNode objects)
  ├─ For each event:
  │  ├─ Retrieve canvas_version_id from Neo4j
  │  ├─ Load composite_image_path
  │  └─ Return timeline with thumbnail + metadata
  └─ Return array of events (chronological)

Frontend: Show timeline of edits, allow click-to-restore
```

---

## 🏗️ Core Components

### 1. **Frontend (React + Vite)**
- **Location:** `frontend/`
- **Key Page:** `src/pages/CapstoneStudio.jsx` (V3 canvas editor)
- **Responsibilities:**
  - Canvas rendering with fabric.js or p5.js
  - Image upload and display
  - Click-based segmentation (point prompts)
  - Mask visualization overlay
  - Object removal confirmation UI
  - Edit history timeline view
  - Real-time feedback during inference

### 2. **Backend (FastAPI)**
- **Location:** `backend/app/`
- **Core Router:** `backend/app/routers/v3_capstone.py`
- **Responsibilities:**
  - Accept image uploads
  - Orchestrate SAM2 segmentation
  - Call LaMa for inpainting
  - Manage scene state (JSON + Neo4j)
  - Compute spatial relationships
  - Record edit events with full provenance
  - Query inpainting context from graph

### 3. **ML Models**
- **SAM 2 (Segment Anything Model 2)**
  - Purpose: Zero-shot object segmentation from point clicks
  - Model: `sam2.1_hiera_large.pt` (2.6 GB, CUDA optimized)
  - Input: Image + click coordinates
  - Output: Binary mask + bounding box
  - Key File: `backend/app/capstone/inference.py` (SAM2 wrapper)

- **LaMa (Large Mask Inpainter)**
  - Purpose: Context-aware object removal and inpainting
  - Model: Big-LaMa variant (4.3 GB, high-quality)
  - Input: Image + mask + optional textual context
  - Output: Inpainted image
  - Key File: `backend/app/capstone/inference.py` (LaMa wrapper + subprocess)

### 4. **Storage Layer**
- **Scene Metadata:** JSON files (`backend/uploads/capstone/scenes/scene_*.json`)
  - SceneDocument with all nodes and relationships
  - Immutable, version-controlled edits
  
- **Image Files:** Local filesystem + S3 (Cloudflare R2)
  - Original images: `capstone/originals/`
  - Masks: `capstone/masks/`
  - Canvas versions: `capstone/canvas_versions/`
  
- **Graph Database:** Neo4j Aura (5.17)
  - Schema: CONSTRAINTS on unique IDs (scene_id, object_id, etc)
  - Relationships: CONTAINS, SPATIAL_RELATIONSHIP, HAS_EVENT
  - Query purpose: Spatial context + relationship inference

---

## 🔑 Key Concepts

### Scene Document
A complete JSON structure containing:
```python
SceneDocument(
    user: UserNode,           # Owner metadata
    scene: SceneNode,         # Canvas info (dimensions, aspect ratio)
    objects: [ImageObjectNode],  # Segmented objects
    text_regions: [TextRegionNode],  # OCR results (optional)
    spatial_relationships: [SpatialRelationshipNode],  # Object relationships
    edit_events: [EditEventNode],  # Full edit history
    canvas_versions: [CanvasVersionNode]  # Composite image versions
)
```

### EditEvent
Immutable record of every change:
```python
EditEventNode(
    event_type: str,           # "REMOVE_OBJECT", "ADD_TEXT", "RESIZE", etc
    before_state_json: dict,   # Full scene state before
    after_state_json: dict,    # Full scene state after
    delta_json: dict,          # Compact representation of what changed
    affected_object_ids: [str],  # Which objects changed
    canvas_version_id: str,    # Link to resulting image
    prev_event_id: str         # Previous event (linked list)
)
```

### Spatial Relationships
Computed after every scene modification:
```python
SpatialRelationshipNode(
    source_object_id: str,     # Object A
    target_object_id: str,     # Object B
    predicate: str,            # "above", "left_of", "overlaps", "adjacent_to"
    distance_px: float,        # Pixel distance between bboxes
    confidence: float          # Certainty of relationship (0.0-1.0)
)
```

---

## 🚀 Quick Start Checklist

```
SETUP:
☐ Install SAM2: pip install git+https://github.com/facebookresearch/sam2.git
☐ Install LaMa: git clone ... external/lama && pip install -r requirements.txt
☐ Download SAM2 checkpoint: checkpoints/sam2.1_hiera_large.pt (2.6 GB)
☐ Download Big-LaMa: models/big-lama (4.3 GB)
☐ Set environment variables in backend/.env
☐ Test setup: python backend/scripts/verify_capstone_models.py

DEVELOPMENT:
☐ Start backend: cd backend && python run_server.py
☐ Start frontend: cd frontend && npm run dev
☐ Visit http://localhost:5173/capstone-studio

TEST FLOW:
☐ Upload test image to /api/v3/scenes/upload
☐ Click object in canvas to segment (SAM2)
☐ Remove object to trigger inpainting (LaMa)
☐ Check /api/v3/scenes/{id}/history for edit events
☐ Verify Neo4j has scene node + relationships
```

---

## 📦 Folder Structure (Key Files Only)

```
backend/
├── app/
│   ├── routers/
│   │   └── v3_capstone.py              ← V3 Endpoints
│   ├── capstone/
│   │   ├── models.py                   ← Pydantic schemas
│   │   ├── inference.py                ← SAM2 + LaMa wrappers
│   │   ├── runtime.py                  ← Config + device resolution
│   │   └── store.py                    ← JSON + Neo4j persistence
│   ├── database/
│   │   ├── capstone_schema_v3.cypher   ← Constraints
│   │   └── neo4j_client.py             ← Connection pool
│   └── rendering/
│       └── storage.py                  ← S3/local put_bytes/fetch_image_bytes
├── checkpoints/
│   └── sam2.1_hiera_large.pt           ← SAM2 weights (2.6 GB)
├── models/
│   └── big-lama/                       ← LaMa weights (4.3 GB)
├── uploads/
│   └── capstone/
│       ├── originals/                  ← User-uploaded images
│       ├── masks/                      ← Segmentation masks
│       └── scenes/                     ← SceneDocument JSON files
├── requirements.txt                    ← Base deps
└── requirements_capstone_v3.txt        ← ML deps (torch, sam2, etc)

frontend/
├── src/
│   ├── pages/
│   │   └── CapstoneStudio.jsx          ← V3 Canvas editor
│   ├── components/
│   │   └── v2/                         ← Reusable UI components
│   ├── services/
│   │   └── v3_client.ts                ← API client
│   └── App.jsx
├── package.json
└── vite.config.js

docs/
└── v3/
    ├── 00_SYSTEM_OVERVIEW_V3.md        ← This file
    ├── 01_ARCHITECTURE_V3.md
    ├── 02_SCHEMA_V3.md
    ├── 03_API_V3.md
    ├── 04_ML_PIPELINES_V3.md
    ├── 05_FRONTEND_V3.md
    ├── 06_INTEGRATION_GUIDE_V3.md
    ├── 07_SETUP_V3.md
    ├── 08_TESTING_V3.md
    └── README_V3.md
```

---

## 🎓 Learning Objectives Achieved

By implementing V3, you demonstrate:

1. **Systems Design**: Coordinating ML models (SAM2, LaMa), storage (JSON + Neo4j), and frontend in a coherent architecture
2. **Graph Data Modeling**: Representing spatial relationships, provenance, and edit history as first-class graph entities
3. **ML Orchestration**: Calling external GPU-intensive models, managing CUDA/CPU fallbacks, handling async inference
4. **Database Design**: Constraint-based uniqueness, relationship traversal for context retrieval
5. **API Design**: RESTful endpoints that manage complex state and provide meaningful feedback
6. **Evaluation Methodology**: Running controlled experiments (blind inpaint vs. graph-guided) on standardized scene snapshots

---

## ⚠️ Critical Implementation Notes

### Memory & Compute
- **SAM2**: ~6 GB VRAM for hiera_large model
- **LaMa Refinement**: ~8-12 GB VRAM during refinement (optional, can disable)
- **Fallback**: If GPU unavailable, SAM2/LaMa can run in mock mode (returns dummy masks/images)

### JSON vs. Neo4j Trade-off
- **Current Implementation**: Primary storage is JSON files on disk
- **Neo4j Role**: Optional sync target for graph queries and relationship visualization
- **Rationale**: JSON allows offline development; Neo4j can be queried for complex spatial analysis

### Mask Precision
- SAM2 produces high-quality masks but may need refinement via dilation/erosion
- SegmentationTuning allows per-operation tuning (e.g., "tight_edges" for precise outlines)

---

## 🔗 Related Documentation

- **Architecture Details**: See [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md)
- **GraphQL Schema**: See [02_SCHEMA_V3.md](./02_SCHEMA_V3.md)
- **API Reference**: See [03_API_V3.md](./03_API_V3.md)
- **ML Pipelines**: See [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md)
- **Frontend Code**: See [05_FRONTEND_V3.md](./05_FRONTEND_V3.md)
- **Integration Guide**: See [06_INTEGRATION_GUIDE_V3.md](./06_INTEGRATION_GUIDE_V3.md)
- **Setup Instructions**: See [07_SETUP_V3.md](./07_SETUP_V3.md)
- **Testing Strategy**: See [08_TESTING_V3.md](./08_TESTING_V3.md)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | April 2026 | Initial V3 implementation with SAM2 + LaMa + graph-backed scene store |
| 3.0.1 (planned) | May 2026 | OCR text region extraction, inline text editing |
| 3.1.0 (planned) | June 2026 | Multi-user collaboration, conflict resolution |

---

**Next:** Read [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md) for component-level details and data flow diagrams.
