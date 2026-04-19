# Capstone V3: Complete API Reference

**Version:** 3.0.0  
**Base URL:** `http://localhost:8000/api/v3` (development) or production URL  
**Authentication:** None (local development); JWT required for production  
**Content-Type:** `application/json` (except file uploads)

---

## 📋 Endpoint Summary

| Method | Path | Purpose | Status |
|--------|------|---------|--------|
| GET | `/capabilities` | Check model availability | ✅ Implemented |
| GET | `/accuracy-presets` | Get tuning presets | ✅ Implemented |
| POST | `/scenes/upload` | Upload image to create scene | ✅ Implemented |
| POST | `/scenes` | Create scene with existing image | ✅ Implemented |
| GET | `/scenes/{scene_id}` | Get complete scene state | ✅ Implemented |
| POST | `/scenes/{scene_id}/objects` | Add object to scene | ✅ Implemented |
| POST | `/scenes/{scene_id}/text-regions` | Add text region | ✅ Implemented |
| POST | `/scenes/{scene_id}/edits` | Record edit event | ✅ Implemented |
| POST | `/scenes/{scene_id}/aspect-ratio` | Update canvas aspect ratio | ✅ Implemented |
| GET | `/scenes/{scene_id}/history` | Get all edit events | ✅ Implemented |
| GET | `/scenes/{scene_id}/inpaint-context/{object_id}` | Get context for inpainting | ✅ Implemented |
| POST | `/scenes/{scene_id}/segment-click` | Click-based segmentation | ✅ Implemented |
| POST | `/scenes/{scene_id}/segment-freehand` | Freehand segmentation | 🔄 Planned |
| POST | `/scenes/{scene_id}/remove-object` | Remove object + inpaint | ✅ Implemented |

---

## 🔧 Endpoints (Detailed)

### 1. **GET /capabilities**

Check if SAM2 and LaMa models are available.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v3/capabilities"
```

**Response (200 OK):**
```json
{
  "sam2": {
    "ready": true,
    "device": "cuda",
    "model_name": "sam2.1_hiera_large",
    "checkpoint_size_mb": 2657
  },
  "lama": {
    "ready": true,
    "device": "cuda",
    "version": "big-lama",
    "checkpoint_size_mb": 4321
  }
}
```

**Response (503 if models unavailable):**
```json
{
  "sam2": {
    "ready": false,
    "error": "SAM2UnavailableError: Module not found"
  },
  "lama": {
    "ready": false,
    "error": "LaMaUnavailableError: Config file missing"
  }
}
```

---

### 2. **GET /accuracy-presets**

Get recommended tuning configurations for segmentation and inpainting.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v3/accuracy-presets"
```

**Response (200 OK):**
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
  },
  "inpainting": {
    "balanced": {
      "mask_dilate_px": 4,
      "neighbor_limit": 5,
      "preserve_text_regions": true,
      "enable_refinement": false,
      "refine_n_iters": 8,
      "refine_lr": 0.0012,
      "refine_max_scales": 2,
      "refine_px_budget": 1400000
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

### 3. **POST /scenes/upload**

Upload an image file to create a new scene.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/upload" \
  -F "file=@/path/to/image.png" \
  -F "title=Living Room Photo" \
  -F "owner_user_id=user_123" \
  -F "email=user@example.com"
```

**Request Body (multipart/form-data):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | ✓ | Image file (PNG, JPG, WebP) |
| title | string | ✗ | Scene title |
| owner_user_id | string | ✗ | Default: "local-user" |
| email | string | ✗ | User email |

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "canvas_width": 1920,
  "canvas_height": 1080,
  "aspect_ratio": "16:9",
  "image_url": "https://s3.example.com/capstone/originals/scene-upload-abc123.png",
  "owner_user_id": "user_123",
  "title": "Living Room Photo",
  "created_at": "2026-04-18T12:34:56.123Z"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Uploaded file is empty"
}
```

**Response (400 Invalid Image):**
```json
{
  "detail": "File is not a readable image"
}
```

---

### 4. **POST /scenes**

Create a scene with an image that's already been uploaded.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes" \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "https://s3.example.com/capstone/originals/scene-upload-abc123.png",
    "canvas_width": 1920,
    "canvas_height": 1080,
    "aspect_ratio": "16:9",
    "owner_user_id": "user_123",
    "title": "Living Room Photo",
    "email": "user@example.com"
  }'
```

**Request Body:**
```python
class CreateSceneRequest(BaseModel):
    image_path: str                    # Required
    canvas_width: int                  # Required, > 0
    canvas_height: int                 # Required, > 0
    aspect_ratio: str                  # Required (e.g., "16:9")
    owner_user_id: str                 # Optional, default "local-user"
    title: Optional[str]               # Optional
    email: Optional[str]               # Optional
```

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "schema_version": "3.0.0",
  "storage_mode": "json+neo4j_optional",
  "scene": {
    "scene_id": "scene_a1b2c3d4e5f6",
    "image_path": "https://s3.example.com/capstone/originals/scene-upload-abc123.png",
    "canvas_width": 1920,
    "canvas_height": 1080,
    "aspect_ratio": "16:9",
    "owner_user_id": "user_123",
    "title": "Living Room Photo",
    "created_at": "2026-04-18T12:34:56.123Z",
    "updated_at": "2026-04-18T12:34:56.123Z",
    "schema_version": "3.0.0",
    "schema_family": "capstone_v3"
  },
  "user": {
    "user_id": "user_123",
    "email": "user@example.com",
    "storage_quota_mb": 2048,
    "created_at": "2026-04-18T12:34:56.123Z",
    "updated_at": "2026-04-18T12:34:56.123Z",
    "schema_version": "3.0.0",
    "schema_family": "capstone_v3"
  },
  "objects": [],
  "edit_events": [
    {
      "event_id": "edit_xyz789",
      "event_type": "INIT",
      "delta_json": {},
      "before_state_json": {},
      "after_state_json": { "scene": {...}, "objects": [] },
      "user_id": "user_123",
      "affected_object_ids": [],
      "prev_event_id": null,
      "canvas_version_id": "ver_init_001",
      "created_at": "2026-04-18T12:34:56.123Z",
      "updated_at": "2026-04-18T12:34:56.123Z",
      "schema_version": "3.0.0"
    }
  ],
  "canvas_versions": [...]
}
```

---

### 5. **GET /scenes/{scene_id}**

Retrieve complete scene state.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6"
```

**Response (200 OK):**
```json
{
  "user": {...},
  "scene": {...},
  "objects": [
    {
      "object_id": "obj_1a2b3c4d5e6f",
      "class_label": "sofa",
      "confidence": 0.98,
      "bbox": {"x": 50, "y": 100, "w": 600, "h": 400},
      "mask_path": "https://s3.example.com/capstone/masks/sofa_1a2b3c.png",
      "z_order": 0,
      "is_locked": false,
      "is_text": false,
      "metadata": {"segmentation_method": "SAM2"},
      "created_at": "2026-04-18T12:35:00.000Z",
      "updated_at": "2026-04-18T12:35:00.000Z",
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
      "created_at": "2026-04-18T12:35:00.000Z",
      "updated_at": "2026-04-18T12:35:00.000Z",
      "schema_version": "3.0.0"
    }
  ],
  "edit_events": [...],
  "canvas_versions": [...]
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Scene not found"
}
```

---

### 6. **POST /scenes/{scene_id}/segment-click**

Click a point in the image to segment an object using SAM2.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/segment-click" \
  -H "Content-Type: application/json" \
  -d '{
    "click_x": 0.4,
    "click_y": 0.35,
    "label": "sofa",
    "confidence": 1.0,
    "register_object": true,
    "z_order": 0,
    "tuning": {
      "multimask_strategy": "best_score",
      "dilate_px": 0,
      "erode_px": 0,
      "keep_largest_component": true,
      "min_area_fraction": 0.001
    }
  }'
```

**Request Body:**
```python
class SegmentClickRequest(BaseModel):
    click_x: float                     # Normalized X (0.0-1.0) [Required]
    click_y: float                     # Normalized Y (0.0-1.0) [Required]
    label: str                         # Object class [Required]
    confidence: float                  # User confidence 0-1 [Optional, default 1.0]
    object_id: Optional[str]           # Override ID [Optional]
    register_object: bool              # Save to scene? [Optional, default True]
    z_order: Optional[int]             # Layer order [Optional]
    tuning: Optional[SegmentationTuning]  # Mask tuning [Optional]
```

**Response (200 OK):**
```json
{
  "object_id": "obj_1a2b3c4d5e6f",
  "mask_url": "https://s3.example.com/capstone/masks/sofa_1a2b3c.png",
  "bbox": {"x": 50, "y": 100, "w": 600, "h": 400},
  "area_fraction": 0.3125,
  "confidence": 0.98,
  "class_label": "sofa",
  "method": "SAM2.segment_from_point",
  "inference_time_ms": 2345,
  "z_order": 0,
  "created_at": "2026-04-18T12:35:00.000Z"
}
```

**Response (503 Model Unavailable):**
```json
{
  "detail": "SAM2 model not available"
}
```

---

### 7. **POST /scenes/{scene_id}/segment-freehand** (Planned)

Draw a freehand path (brush or lasso) to segment objects.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/segment-freehand" \
  -H "Content-Type: application/json" \
  -d '{
    "paths": [
      {
        "points": [
          {"x": 0.1, "y": 0.2},
          {"x": 0.2, "y": 0.25},
          {"x": 0.3, "y": 0.2},
          {"x": 0.4, "y": 0.3}
        ]
      }
    ],
    "mode": "brush",
    "brush_size_px": 24,
    "label": "sofa",
    "confidence": 1.0,
    "register_object": true,
    "sam_refine": true,
    "tuning": {"multimask_strategy": "best_score"}
  }'
```

**Request Body:**
```python
class SegmentFreehandRequest(BaseModel):
    paths: List[FreehandPath]          # List of paths [Required, min 1, max 256]
    mode: Literal["brush", "lasso"]    # Interaction mode [Optional, default "brush"]
    brush_size_px: int                 # Brush diameter [Optional, default 24]
    label: str                         # Object class [Required]
    confidence: float                  # Confidence 0-1 [Optional, default 1.0]
    object_id: Optional[str]           # Override ID [Optional]
    register_object: bool              # Save? [Optional, default True]
    z_order: Optional[int]             # Layer order [Optional]
    sam_refine: bool                   # Refine with SAM2? [Optional, default True]
    tuning: Optional[SegmentationTuning]  # Tuning [Optional]
```

---

### 8. **POST /scenes/{scene_id}/remove-object**

Remove an object and inpaint the background.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/remove-object" \
  -H "Content-Type: application/json" \
  -d '{
    "object_id": "obj_1a2b3c4d5e6f",
    "record_event": true,
    "tuning": {
      "mask_dilate_px": 4,
      "neighbor_limit": 5,
      "preserve_text_regions": true,
      "enable_refinement": false
    }
  }'
```

**Request Body:**
```python
class RemoveObjectRequest(BaseModel):
    object_id: str                     # Object to remove [Required]
    record_event: bool                 # Log as EditEvent? [Optional, default True]
    tuning: Optional[InpaintTuning]    # Inpainting config [Optional]
```

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "operation": "remove_object",
  "removed_object_id": "obj_1a2b3c4d5e6f",
  "removed_class_label": "sofa",
  "removed_area_px": 240000,
  "inpaint_context": {
    "neighbors": [
      {
        "object_id": "obj_7g8h9i0j1k2l",
        "class_label": "lamp",
        "predicate": "left_of",
        "distance_px": 150.0
      }
    ],
    "text_regions": [],
    "mask_dilate_px": 4
  },
  "inpaint_method": "LaMa",
  "inpaint_time_ms": 7234,
  "new_canvas_version_id": "ver_after_removal",
  "new_canvas_image_url": "https://s3.example.com/capstone/canvas_versions/scene_a1b2c3d4e5f6_v2.png",
  "edit_event_id": "edit_removal_001",
  "created_at": "2026-04-18T12:36:00.000Z"
}
```

**Response (404 Scene Not Found):**
```json
{
  "detail": "Scene not found"
}
```

**Response (503 LaMa Unavailable):**
```json
{
  "detail": "LaMa model not available"
}
```

---

### 9. **POST /scenes/{scene_id}/objects**

Manually add an object to a scene.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/objects" \
  -H "Content-Type: application/json" \
  -d '{
    "class_label": "painting",
    "bbox": {"x": 1200, "y": 50, "w": 300, "h": 400},
    "confidence": 0.95,
    "mask_path": "https://s3.example.com/capstone/masks/painting_xyz.png",
    "z_order": 1,
    "is_locked": false,
    "metadata": {"source": "manual", "artist": "unknown"}
  }'
```

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "objects": [
    {
      "object_id": "obj_1a2b3c4d5e6f",
      "class_label": "sofa",
      "confidence": 0.98,
      "bbox": {"x": 50, "y": 100, "w": 600, "h": 400},
      "z_order": 0,
      "is_locked": false,
      "is_text": false,
      "metadata": {},
      "created_at": "2026-04-18T12:35:00.000Z"
    },
    {
      "object_id": "obj_new_xyz789",
      "class_label": "painting",
      "confidence": 0.95,
      "bbox": {"x": 1200, "y": 50, "w": 300, "h": 400},
      "z_order": 1,
      "is_locked": false,
      "is_text": false,
      "metadata": {"source": "manual"},
      "created_at": "2026-04-18T12:37:00.000Z"
    }
  ],
  "spatial_relationships": [
    {
      "rel_id": "rel_xyz",
      "source_object_id": "obj_1a2b3c4d5e6f",
      "target_object_id": "obj_new_xyz789",
      "predicate": "below",
      "confidence": 0.99,
      "distance_px": 400.0
    }
  ]
}
```

---

### 10. **POST /scenes/{scene_id}/text-regions**

Add detected or manually created text to a scene.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/text-regions" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Welcome to Our Home",
    "bbox": {"x": 50, "y": 750, "w": 800, "h": 80},
    "font_family": "Arial",
    "font_size": 48,
    "color_hex": "#FFFFFF",
    "is_embedded": true,
    "ocr_confidence": 0.92,
    "attached_object_id": null
  }'
```

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "objects": [...],
  "text_regions": [
    {
      "text_id": "text_abc123def456",
      "object_id": "obj_text_region_001",
      "attached_object_id": null,
      "raw_text": "Welcome to Our Home",
      "font_family": "Arial",
      "font_size": 48,
      "color_hex": "#FFFFFF",
      "is_embedded": true,
      "ocr_confidence": 0.92,
      "bbox": {"x": 50, "y": 750, "w": 800, "h": 80},
      "created_at": "2026-04-18T12:38:00.000Z"
    }
  ],
  "spatial_relationships": [...]
}
```

---

### 11. **POST /scenes/{scene_id}/edits**

Record an edit event manually (e.g., for external modifications).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/edits" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "MANUAL_EDIT",
    "delta_json": {"operation": "user_adjustment", "details": "resized object"},
    "before_state_json": {"objects": [...previous state...]},
    "after_state_json": {"objects": [...new state...]},
    "affected_object_ids": ["obj_1a2b3c4d5e6f"],
    "user_id": "user_123",
    "composite_image_path": "https://s3.example.com/capstone/canvas_versions/scene_a1b2c3d4e5f6_v3.png"
  }'
```

**Response (200 OK):**
```json
{
  "event_id": "edit_manual_001",
  "event_type": "MANUAL_EDIT",
  "delta_json": {"operation": "user_adjustment"},
  "before_state_json": {...},
  "after_state_json": {...},
  "user_id": "user_123",
  "affected_object_ids": ["obj_1a2b3c4d5e6f"],
  "prev_event_id": "edit_removal_001",
  "canvas_version_id": "ver_after_manual",
  "created_at": "2026-04-18T12:39:00.000Z"
}
```

---

### 12. **GET /scenes/{scene_id}/history**

Retrieve complete edit history (all EditEvents).

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/history"
```

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "history": [
    {
      "event_id": "edit_init_001",
      "event_type": "INIT",
      "created_at": "2026-04-18T12:34:56.000Z",
      "affected_object_ids": [],
      "delta_json": {}
    },
    {
      "event_id": "edit_segment_001",
      "event_type": "SEGMENT_CLICK",
      "created_at": "2026-04-18T12:35:00.000Z",
      "affected_object_ids": ["obj_1a2b3c4d5e6f"],
      "delta_json": {
        "segmented_object_id": "obj_1a2b3c4d5e6f",
        "class_label": "sofa",
        "method": "SAM2"
      }
    },
    {
      "event_id": "edit_removal_001",
      "event_type": "REMOVE_OBJECT",
      "created_at": "2026-04-18T12:36:00.000Z",
      "affected_object_ids": ["obj_1a2b3c4d5e6f"],
      "delta_json": {
        "removed_object_id": "obj_1a2b3c4d5e6f",
        "inpaint_context": "..."
      }
    }
  ],
  "total_events": 3,
  "current_canvas_version_id": "ver_after_removal"
}
```

---

### 13. **GET /scenes/{scene_id}/inpaint-context/{object_id}**

Get contextual information about neighboring objects (for inpainting).

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/inpaint-context/obj_1a2b3c4d5e6f?limit=5"
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 5 | Max neighbors to return |

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "object_id": "obj_1a2b3c4d5e6f",
  "object_class": "sofa",
  "object_bbox": {"x": 50, "y": 100, "w": 600, "h": 400},
  "neighbors": [
    {
      "object_id": "obj_7g8h9i0j1k2l",
      "class_label": "lamp",
      "predicate": "left_of",
      "distance_px": 150.0,
      "bbox": {"x": -100, "y": 80, "w": 80, "h": 120}
    },
    {
      "object_id": "obj_2m3n4o5p6q7r",
      "class_label": "wall",
      "predicate": "overlaps",
      "distance_px": 0.0,
      "bbox": {"x": 0, "y": 0, "w": 1920, "h": 200}
    }
  ],
  "text_regions": [
    {
      "text_id": "text_xyz",
      "raw_text": "Modern Design",
      "bbox": {"x": 100, "y": 500, "w": 300, "h": 50},
      "overlaps_target": false
    }
  ],
  "inpaint_prompt": "sofa removed, preserve lamp on left and wall colors",
  "mask_area_px": 240000,
  "mask_area_fraction": 0.1307
}
```

---

### 14. **POST /scenes/{scene_id}/aspect-ratio**

Update the canvas aspect ratio.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v3/scenes/scene_a1b2c3d4e5f6/aspect-ratio" \
  -H "Content-Type: application/json" \
  -d '{
    "aspect_ratio": "1:1",
    "canvas_width": 1080,
    "canvas_height": 1080,
    "composite_image_path": "https://s3.example.com/capstone/canvas_versions/scene_resized.png"
  }'
```

**Request Body:**
```python
class UpdateAspectRatioRequest(BaseModel):
    aspect_ratio: str              # New ratio (e.g., "1:1", "4:3") [Required]
    canvas_width: int              # New width [Required, > 0]
    canvas_height: int             # New height [Required, > 0]
    composite_image_path: Optional[str]  # Image after resize [Optional]
```

**Response (200 OK):**
```json
{
  "scene_id": "scene_a1b2c3d4e5f6",
  "aspect_ratio_old": "16:9",
  "aspect_ratio_new": "1:1",
  "canvas_width_old": 1920,
  "canvas_width_new": 1080,
  "canvas_height_old": 1080,
  "canvas_height_new": 1080,
  "edit_event_id": "edit_aspect_001",
  "created_at": "2026-04-18T12:40:00.000Z"
}
```

---

## 🔐 Error Responses

All endpoints return standard HTTP error codes:

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad Request | Invalid JSON, missing required field |
| 404 | Not Found | Scene doesn't exist |
| 503 | Service Unavailable | GPU model not loaded |

**Standard Error Format:**
```json
{
  "detail": "Descriptive error message"
}
```

---

## 📊 Rate Limiting (Future)

Currently, no rate limiting. Plan to add:
- 100 requests/minute per IP (development)
- 1000 requests/minute per API key (production)

---

## 🧪 Testing Endpoints

**Test Workflow:**
```bash
# 1. Upload image
SCENE_ID=$(curl -s -X POST "http://localhost:8000/api/v3/scenes/upload" \
  -F "file=@test_image.png" \
  -F "title=Test" | jq -r '.scene_id')

# 2. Segment object
curl -X POST "http://localhost:8000/api/v3/scenes/$SCENE_ID/segment-click" \
  -H "Content-Type: application/json" \
  -d '{"click_x": 0.5, "click_y": 0.5, "label": "object"}'

# 3. Remove object
curl -X POST "http://localhost:8000/api/v3/scenes/$SCENE_ID/remove-object" \
  -H "Content-Type: application/json" \
  -d '{"object_id": "obj_...", "record_event": true}'

# 4. Check history
curl -X GET "http://localhost:8000/api/v3/scenes/$SCENE_ID/history"
```

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | April 2026 | Initial API spec with 11 endpoints |
| 3.0.1 (planned) | May 2026 | Freehand segmentation, rate limiting |
| 3.1.0 (planned) | June 2026 | Batch operations, search |

---

**Next:** Read [04_ML_PIPELINES_V3.md](./04_ML_PIPELINES_V3.md) for details on SAM2 and LaMa integration.
