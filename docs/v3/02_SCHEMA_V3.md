# Capstone V3: Data Schema & Models

**Version:** 3.0.0  
**Audience:** Data Engineers, Full-Stack Developers  
**Purpose:** Complete specification of all Pydantic models, graph node types, and their relationships

---

## 🎯 Schema Overview

V3 uses a **graph-based data model** where:
- **Nodes** represent entities (Scenes, Objects, TextRegions, Edits)
- **Relationships** encode spatial and temporal connections
- **Immutability** ensures edit history is tamper-proof
- **Versioning** allows rollback to any prior state

### Core Principles
1. **Timestamped**: Every node has `created_at`, `updated_at`
2. **Versioned**: `schema_version` = "3.0.0" on all nodes
3. **Identified**: Unique UUID-like IDs (`scene_id`, `object_id`, etc)
4. **Constrained**: Pydantic validation + Neo4j constraints

---

## 📦 Pydantic Models (Python Type Definitions)

**File:** `backend/app/capstone/models.py`

All models inherit from `CapstoneModel` which extends `pydantic.BaseModel` with:
- `extra="forbid"` — no unknown fields allowed
- UUID generation for IDs
- UTC timestamp generation

---

### 1. **Core Node Types**

#### `SceneNode`
Represents a single canvas/image workspace.

```python
class SceneNode(TimestampedNode):
    scene_id: str                          # "scene_a1b2c3d4e5f6"
    image_path: str                        # "https://s3.../original.png"
    canvas_width: int                      # e.g., 1920 (pixels)
    canvas_height: int                     # e.g., 1080 (pixels)
    aspect_ratio: str                      # e.g., "16:9"
    owner_user_id: str                     # "local-user" or user UUID
    title: Optional[str]                   # "Living Room Photo"
    
    # Inherited from TimestampedNode:
    created_at: datetime                   # "2026-04-18T12:34:56Z"
    updated_at: datetime
    schema_version: str                    # "3.0.0"
    schema_family: str                     # "capstone_v3"
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_scene_id IF NOT EXISTS
FOR (s:CapstoneScene) REQUIRE s.scene_id IS UNIQUE;
```

**Usage Example:**
```python
scene = SceneNode(
    image_path="https://s3.../capstone/originals/photo.png",
    canvas_width=1920,
    canvas_height=1080,
    aspect_ratio="16:9",
    owner_user_id="user_123",
    title="Living Room"
)
# Generated automatically:
# - scene_id: "scene_xyz789"
# - created_at: datetime.now(utc)
# - schema_version: "3.0.0"
```

---

#### `UserNode`
Represents a user account (currently single-user).

```python
class UserNode(TimestampedNode):
    user_id: str                           # "local-user" (single-user for now)
    email: Optional[str]                   # "user@example.com"
    storage_quota_mb: int                  # 2048 MB default
    
    # Inherited:
    created_at: datetime
    updated_at: datetime
    schema_version: str
    schema_family: str
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_user_id IF NOT EXISTS
FOR (u:CapstoneUser) REQUIRE u.user_id IS UNIQUE;
```

---

#### `BoundingBox`
Represents a rectangular region (no timestamps, pure geometry).

```python
class BoundingBox(CapstoneModel):
    x: int                                 # Left edge (pixels, >= 0)
    y: int                                 # Top edge (pixels, >= 0)
    w: int                                 # Width (pixels, > 0)
    h: int                                 # Height (pixels, > 0)
    
    # Computed properties:
    @property
    def x2(self) -> int:                   # x + w (right edge)
        return self.x + self.w
    
    @property
    def y2(self) -> int:                   # y + h (bottom edge)
        return self.y + self.h
    
    @property
    def center_x(self) -> float:           # Center X
        return self.x + (self.w / 2.0)
    
    @property
    def center_y(self) -> float:           # Center Y
        return self.y + (self.h / 2.0)
```

**Validation:**
- `x >= 0`, `y >= 0` (can't be negative)
- `w > 0`, `h > 0` (must have positive area)

**Usage Example:**
```python
bbox = BoundingBox(x=100, y=200, w=300, h=400)
print(bbox.x2)        # 400
print(bbox.center_x)  # 250
```

---

#### `ImageObjectNode`
Represents a segmented object in the scene.

```python
class ImageObjectNode(TimestampedNode):
    object_id: str                         # "obj_1a2b3c4d5e6f" (auto-generated)
    class_label: str                       # "chair", "table", "person", etc
    confidence: float                      # 0.0-1.0 (segmentation confidence)
    bbox: BoundingBox                      # Bounding box coordinates
    mask_path: Optional[str]               # "https://s3.../masks/chair.png"
    z_order: int                           # Layering order (0=background)
    is_locked: bool                        # Can't be edited if True
    is_text: bool                          # True if this is a text region
    metadata: Dict[str, Any]               # Custom key-value data
    
    # Inherited:
    created_at: datetime
    updated_at: datetime
    schema_version: str
    schema_family: str
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_object_id IF NOT EXISTS
FOR (o:CapstoneImageObject) REQUIRE o.object_id IS UNIQUE;
```

**Usage Examples:**

```python
# Object created from SAM2 segmentation
obj = ImageObjectNode(
    class_label="sofa",
    confidence=0.98,
    bbox=BoundingBox(x=50, y=100, w=600, h=400),
    mask_path="https://s3.../masks/sofa_a1b2c3.png",
    z_order=0,
    is_locked=False,
    is_text=False,
    metadata={"segmentation_method": "SAM2"}
)

# Object for text region (special case)
text_obj = ImageObjectNode(
    class_label="text_region",
    confidence=0.95,
    bbox=BoundingBox(x=20, y=20, w=200, h=50),
    is_text=True,
    z_order=10,
    metadata={"attached_to_object_id": "obj_1a2b3c4d5e6f"}
)
```

---

#### `TextRegionNode`
Represents detected or manually added text (OCR or annotation).

```python
class TextRegionNode(TimestampedNode):
    text_id: str                           # "text_abc123def456" (auto-generated)
    object_id: str                         # Points to corresponding ImageObjectNode
    attached_object_id: Optional[str]      # If text is attached to an object
    raw_text: str                          # "Welcome to our home"
    font_family: Optional[str]             # "Arial", "Helvetica", etc
    font_size: Optional[int]               # 24 (pixels)
    color_hex: Optional[str]               # "#FF0000" (red)
    is_embedded: bool                      # True if rendered into image
    ocr_confidence: float                  # 0.0-1.0 (OCR accuracy)
    bbox: BoundingBox                      # Text region bounds
    
    # Inherited:
    created_at: datetime
    updated_at: datetime
    schema_version: str
    schema_family: str
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_text_id IF NOT EXISTS
FOR (t:CapstoneTextRegion) REQUIRE t.text_id IS UNIQUE;
```

**Usage Example:**
```python
text = TextRegionNode(
    object_id="obj_text_region_001",
    attached_object_id=None,  # Floating text, not attached
    raw_text="Best furniture store in town",
    font_family="Arial",
    font_size=32,
    color_hex="#FFFFFF",
    is_embedded=True,
    ocr_confidence=0.92,
    bbox=BoundingBox(x=50, y=750, w=800, h=80)
)
```

---

#### `SpatialRelationshipNode`
Represents spatial relationships between objects (computed automatically).

```python
class SpatialRelationshipNode(TimestampedNode):
    rel_id: str                            # "rel_xyz789abc123" (auto-generated)
    source_object_id: str                  # Object A
    target_object_id: str                  # Object B
    predicate: Literal[                    # Type of relationship
        "above",
        "below",
        "left_of",
        "right_of",
        "overlaps",
        "contains",
        "adjacent_to"
    ]
    confidence: float                      # 0.0-1.0
    distance_px: float                     # Pixel distance (center-to-center)
    
    # Inherited:
    created_at: datetime
    updated_at: datetime
    schema_version: str
    schema_family: str
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_rel_id IF NOT EXISTS
FOR (r:CapstotneRelationship) REQUIRE r.rel_id IS UNIQUE;
```

**Computation Algorithm:**
```python
def compute_spatial_relationships(objects: List[ImageObjectNode]):
    relationships = []
    for i, obj_a in enumerate(objects):
        for obj_b in objects[i+1:]:
            # Compute predicates
            if obj_a.bbox.y2 < obj_b.bbox.y:
                predicate = "above"
            elif obj_a.bbox.y > obj_b.bbox.y2:
                predicate = "below"
            elif obj_a.bbox.x2 < obj_b.bbox.x:
                predicate = "left_of"
            elif obj_a.bbox.x > obj_b.bbox.x2:
                predicate = "right_of"
            else:  # Overlapping or adjacent
                if _overlaps(obj_a.bbox, obj_b.bbox):
                    predicate = "overlaps"
                elif _contains(obj_a.bbox, obj_b.bbox):
                    predicate = "contains"
                else:
                    predicate = "adjacent_to"
            
            # Compute distance
            center_dist = math.hypot(
                obj_a.bbox.center_x - obj_b.bbox.center_x,
                obj_a.bbox.center_y - obj_b.bbox.center_y
            )
            
            relationships.append(SpatialRelationshipNode(
                source_object_id=obj_a.object_id,
                target_object_id=obj_b.object_id,
                predicate=predicate,
                confidence=0.95,
                distance_px=center_dist
            ))
    return relationships
```

---

#### `EditEventNode`
Immutable record of every change (forms a linked list).

```python
class EditEventNode(TimestampedNode):
    event_id: str                          # "edit_aaa111bbb222" (auto-generated)
    event_type: str                        # "INIT", "REMOVE_OBJECT", "ADD_TEXT", etc
    delta_json: Dict[str, Any]             # What changed (compact)
    before_state_json: Dict[str, Any]      # Full scene state BEFORE
    after_state_json: Dict[str, Any]       # Full scene state AFTER
    user_id: str                           # Who made the change
    affected_object_ids: List[str]         # Objects impacted
    prev_event_id: Optional[str]           # Link to previous event (chain)
    canvas_version_id: Optional[str]       # Link to resulting image
    
    # Inherited:
    created_at: datetime
    updated_at: datetime
    schema_version: str
    schema_family: str
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_edit_id IF NOT EXISTS
FOR (e:CapstoneEditEvent) REQUIRE e.event_id IS UNIQUE;
```

**Usage Examples:**

```python
# INIT event (scene created)
init_event = EditEventNode(
    event_type="INIT",
    delta_json={},
    before_state_json={},
    after_state_json={
        "scene": {...},
        "objects": [],
        "text_regions": [],
        "spatial_relationships": []
    },
    user_id="local-user",
    affected_object_ids=[],
    prev_event_id=None,
    canvas_version_id="ver_init_001"
)

# REMOVE_OBJECT event
remove_event = EditEventNode(
    event_type="REMOVE_OBJECT",
    delta_json={
        "removed_object_id": "obj_1a2b3c4d5e6f",
        "mask_area_px": 120000,
        "inpaint_context": "sofa on left, lamp above"
    },
    before_state_json={
        "objects": [
            {"object_id": "obj_1a2b3c4d5e6f", "class_label": "chair", ...}
        ]
    },
    after_state_json={
        "objects": []  # chair removed
    },
    user_id="local-user",
    affected_object_ids=["obj_1a2b3c4d5e6f"],
    prev_event_id="edit_init_001",
    canvas_version_id="ver_after_removal"
)
```

---

#### `CanvasVersionNode`
Represents a snapshot of the composite image at a point in time.

```python
class CanvasVersionNode(TimestampedNode):
    version_id: str                        # "ver_s1t2u3v4w5x6" (auto-generated)
    composite_image_path: str              # "https://s3.../canvas_v2.png"
    graph_snapshot_json: Dict[str, Any]    # Scene state at this version
    is_current: bool                       # Is this the latest version?
    
    # Inherited:
    created_at: datetime
    updated_at: datetime
    schema_version: str
    schema_family: str
```

**Constraints (Neo4j):**
```cypher
CREATE CONSTRAINT capstone_version_id IF NOT EXISTS
FOR (v:CapstoneCanvasVersion) REQUIRE v.version_id IS UNIQUE;
```

**Usage Example:**
```python
version = CanvasVersionNode(
    composite_image_path="https://s3.../canvas_versions/scene_a1b2c3_v2.png",
    graph_snapshot_json={
        "objects": [],  # After deletion
        "text_regions": [],
        "spatial_relationships": []
    },
    is_current=True
)
```

---

### 2. **Container Type: SceneDocument**

Top-level container holding all related data:

```python
class SceneDocument(CapstoneModel):
    user: UserNode                         # Owner info
    scene: SceneNode                       # Canvas metadata
    objects: List[ImageObjectNode]         # All segmented objects
    text_regions: List[TextRegionNode]     # All detected/added text
    spatial_relationships: List[SpatialRelationshipNode]  # Object relationships
    edit_events: List[EditEventNode]       # Full edit history
    canvas_versions: List[CanvasVersionNode]  # Image snapshots
```

**Serialization (to JSON):**
```json
{
  "user": { ... },
  "scene": { ... },
  "objects": [ ... ],
  "text_regions": [ ... ],
  "spatial_relationships": [ ... ],
  "edit_events": [ ... ],
  "canvas_versions": [ ... ]
}
```

---

### 3. **Request Models (API Input)**

#### `CreateSceneRequest`
Input to `POST /api/v3/scenes` or `POST /api/v3/scenes/upload`

```python
class CreateSceneRequest(CapstoneModel):
    image_path: str                        # URL to pre-uploaded image
    canvas_width: int                      # Image width
    canvas_height: int                     # Image height
    aspect_ratio: str                      # "16:9", "1:1", etc
    owner_user_id: str                     # "local-user"
    title: Optional[str]                   # Scene title
    email: Optional[str]                   # Owner email
```

---

#### `CreateObjectRequest`
Input to `POST /api/v3/scenes/{id}/objects`

```python
class CreateObjectRequest(CapstoneModel):
    class_label: str                       # Object type
    bbox: BoundingBox                      # Region
    confidence: float                      # Confidence 0-1
    mask_path: Optional[str]               # URL to mask PNG
    z_order: int                           # Layer order
    is_locked: bool                        # Can't be edited
    metadata: Dict[str, Any]               # Custom data
```

---

#### `SegmentClickRequest`
Input to `POST /api/v3/scenes/{id}/segment-click`

```python
class SegmentClickRequest(CapstoneModel):
    click_x: float                         # Normalized X (0-1)
    click_y: float                         # Normalized Y (0-1)
    label: str                             # Object class
    confidence: float                      # User's confidence (0-1)
    object_id: Optional[str]               # Override generated ID
    register_object: bool                  # Save to scene?
    z_order: Optional[int]                 # Layer order
    tuning: Optional[SegmentationTuning]   # Mask refinement config
```

---

#### `RemoveObjectRequest`
Input to `POST /api/v3/scenes/{id}/remove-object`

```python
class RemoveObjectRequest(CapstoneModel):
    object_id: str                         # Which object to remove
    record_event: bool                     # Log as EditEvent?
    tuning: Optional[InpaintTuning]        # Inpainting config
```

---

### 4. **Tuning Models (ML Configuration)**

#### `SegmentationTuning`
Controls SAM2 mask refinement:

```python
class SegmentationTuning(CapstoneModel):
    multimask_strategy: Literal["best_score", "largest_mask"]
                                           # Which mask to select
    dilate_px: int                         # Expand mask (0-64 pixels)
    erode_px: int                          # Shrink mask (0-64 pixels)
    keep_largest_component: bool           # Remove small fragments?
    min_area_fraction: float               # Minimum mask size (0-1)
```

**Accuracy Presets (from `/api/v3/accuracy-presets`):**

```json
{
  "segmentation": {
    "balanced": {
      "multimask_strategy": "best_score",
      "dilate_px": 0,
      "erode_px": 0,
      "keep_largest_component": true,
      "min_area_fraction": 0.001
    },
    "tight_edges": {
      "multimask_strategy": "best_score",
      "dilate_px": 0,
      "erode_px": 1,
      "keep_largest_component": true,
      "min_area_fraction": 0.0005
    },
    "object_recall": {
      "multimask_strategy": "largest_mask",
      "dilate_px": 2,
      "erode_px": 0,
      "keep_largest_component": true,
      "min_area_fraction": 0.002
    }
  }
}
```

---

#### `InpaintTuning`
Controls LaMa inpainting behavior:

```python
class InpaintTuning(CapstoneModel):
    mask_dilate_px: int                    # Expand removal mask (0-64)
    neighbor_limit: int                    # Max neighbors to preserve (1-20)
    preserve_text_regions: bool            # Don't inpaint text?
    enable_refinement: bool                # Run refinement pass?
    refine_gpu_ids: Optional[str]          # GPU allocation
    refine_modulo: Optional[int]           # Refinement stride
    refine_n_iters: int                    # Refinement iterations
    refine_lr: float                       # Learning rate
    refine_min_side: int                   # Minimum dimension
    refine_max_scales: int                 # Multi-scale levels
    refine_px_budget: int                  # Memory budget (pixels)
```

**Accuracy Presets (from `/api/v3/accuracy-presets`):**

```json
{
  "inpainting": {
    "balanced": {
      "mask_dilate_px": 4,
      "neighbor_limit": 5,
      "preserve_text_regions": true,
      "enable_refinement": false
    },
    "background_cleanup": {
      "mask_dilate_px": 8,
      "neighbor_limit": 6,
      "preserve_text_regions": true,
      "enable_refinement": false
    },
    "detail_preserve": {
      "mask_dilate_px": 2,
      "neighbor_limit": 4,
      "preserve_text_regions": true,
      "enable_refinement": false
    },
    "refine_soft": {
      "mask_dilate_px": 2,
      "neighbor_limit": 5,
      "preserve_text_regions": true,
      "enable_refinement": true,
      "refine_n_iters": 6,
      "refine_lr": 0.001,
      "refine_max_scales": 2,
      "refine_px_budget": 1200000
    },
    "hq_refine": {
      "mask_dilate_px": 3,
      "neighbor_limit": 5,
      "preserve_text_regions": true,
      "enable_refinement": true,
      "refine_n_iters": 10,
      "refine_lr": 0.0012,
      "refine_max_scales": 2,
      "refine_px_budget": 1400000
    }
  }
}
```

---

## 🗄️ Neo4j Schema (Optional)

**Nodes:**
```cypher
LABEL: CapstoneScene
PROPERTIES:
  - scene_id (UNIQUE)
  - image_path
  - canvas_width
  - canvas_height
  - aspect_ratio
  - owner_user_id
  - title
  - created_at, updated_at
  - schema_version

LABEL: CapstoneUser
PROPERTIES:
  - user_id (UNIQUE)
  - email
  - storage_quota_mb
  - created_at, updated_at
  - schema_version

LABEL: CapstoneImageObject
PROPERTIES:
  - object_id (UNIQUE)
  - class_label
  - confidence
  - bbox (serialized as JSON string)
  - mask_path
  - z_order
  - is_locked
  - is_text
  - metadata (JSON string)
  - created_at, updated_at
  - schema_version

LABEL: CapstoneTextRegion
PROPERTIES:
  - text_id (UNIQUE)
  - object_id
  - attached_object_id
  - raw_text
  - font_family
  - font_size
  - color_hex
  - is_embedded
  - ocr_confidence
  - bbox (JSON string)
  - created_at, updated_at
  - schema_version

LABEL: CapstoneEditEvent
PROPERTIES:
  - event_id (UNIQUE)
  - event_type
  - delta_json (JSON string)
  - before_state_json (JSON string)
  - after_state_json (JSON string)
  - user_id
  - affected_object_ids (JSON array)
  - prev_event_id
  - canvas_version_id
  - created_at, updated_at
  - schema_version

LABEL: CapstoneCanvasVersion
PROPERTIES:
  - version_id (UNIQUE)
  - composite_image_path
  - graph_snapshot_json (JSON string)
  - is_current
  - created_at, updated_at
  - schema_version
```

**Relationships:**
```cypher
(CapstoneScene)-[:OWNED_BY]->(CapstoneUser)
(CapstoneScene)-[:CONTAINS]->(CapstoneImageObject)
(CapstoneScene)-[:CONTAINS]->(CapstoneTextRegion)
(CapstoneImageObject)-[:SPATIAL_RELATIONSHIP]->(CapstoneImageObject)
(CapstoneScene)-[:HAS_EVENT]->(CapstoneEditEvent)
(CapstoneScene)-[:HAS_VERSION]->(CapstoneCanvasVersion)
```

---

## 🔍 JSON Serialization Notes

### Nested Dict Handling
⚠️ **CRITICAL**: Neo4j doesn't accept nested dicts as node properties.

**WRONG:**
```python
# This will fail when syncing to Neo4j:
node_props = {
    "delta_json": {"removed": {"object_id": "...", "mask": {...}}}
}
```

**CORRECT:**
```python
# Serialize to JSON string before sending to Neo4j:
node_props = {
    "delta_json": json.dumps({"removed": {"object_id": "...", "mask": {...}}})
}
```

This is handled automatically in `backend/app/capstone/store.py` by:
```python
def _sync_to_neo4j(doc: SceneDocument):
    # Serialize all dict/list fields to JSON strings
    for event in doc.edit_events:
        props = {
            "event_id": event.event_id,
            "delta_json": json.dumps(event.delta_json),  # ← Serialize
            "before_state_json": json.dumps(event.before_state_json),
            "after_state_json": json.dumps(event.after_state_json),
            # ... other fields
        }
        # Write to Neo4j
```

---

## 📝 Version History

| Field | V1 | V2 | V3 |
|-------|----|----|-----|
| Schema Version | "1.0.0" | "2.0.0" | "3.0.0" |
| Schema Family | "brand_v1" | "scene_v2" | "capstone_v3" |
| Primary Entities | Brand, Product, Asset | Scene, CompositionLayer | Scene, ImageObject, TextRegion, EditEvent |
| Graph Type | Knowledge Graph | Scene Composition | Spatial Graph + Event Log |

---

## 🔗 Related Documentation

- **Architecture**: See [01_ARCHITECTURE_V3.md](./01_ARCHITECTURE_V3.md)
- **API Reference**: See [03_API_V3.md](./03_API_V3.md) for request/response examples
- **ML Pipelines**: See [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) for tuning details

---

**Next:** Read [03_API_V3.md](./03_API_V3.md) for complete API endpoint documentation.
