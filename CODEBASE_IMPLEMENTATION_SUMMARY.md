# Capstone V3 Implementation Deep Dive

**Project**: GraphRAG-Guided Compositional Image Generation with Scene Graph Control  
**Date**: April 19, 2026  
**Scope**: SAM2 segmentation, LaMa inpainting, graph relationships, performance metrics

---

## 1. SAM2 Segmentation Implementation

### Overview
SAM2 (Segment Anything Model 2) provides interactive image segmentation with two pathways:
- **Click-based segmentation**: Point-to-mask prediction
- **Freehand segmentation**: Brush/lasso strokes refined with SAM2

**Key File**: [backend/app/capstone/inference.py](backend/app/capstone/inference.py) (Lines 1–400)

### SAM2ClickSegmenter Class

#### Status Method (Lines 241–253)
```python
def status(self) -> Dict[str, object]:
    checkpoint = self.settings.resolved_sam2_checkpoint
    return {
        "package": has_sam2(),
        "torch": has_torch(),
        "checkpoint_path": str(checkpoint),
        "checkpoint_exists": checkpoint.exists(),
        "config": self.settings.sam2_config,
        "device": self.device,
        "ready": has_sam2() and checkpoint.exists(),
    }
```
- Verifies SAM2 package availability, PyTorch presence, checkpoint file existence
- Defaults: `checkpoints/sam2.1_hiera_large.pt` (2.6 GB)
- Config: `configs/sam2.1/sam2.1_hiera_l.yaml`
- Returns readiness status object

#### Click Segmentation (Lines 269–333)
```python
def segment_from_click(
    self,
    image_url: str,
    click_x: float,
    click_y: float,
    label: str = "object",
    tuning: Optional[SegmentationTuning] = None,
) -> Dict
```

**Process**:
1. Load image from URL (JPEG/PNG), convert to RGB
2. Create normalized click coordinates: `point_coords = [[click_x * w, click_y * h]]` (line 289)
3. Call SAM2 predictor with:
   - Image array
   - Positive point label (1)
   - `multimask_output=True` (returns 3 mask candidates)
4. **Mask Selection Strategy** (line 297):
   - Default: `best_idx = argmax(scores)` (confidence-based)
   - Alternative: `largest_mask` strategy uses max area
5. **Tuning Applied** (line 299):
   - Refine mask via morphological operations
   - Validate minimum area fraction

**Output**:
```json
{
    "mask_url": "s3://capstone/masks/...",
    "bbox": [x0, y0, x1, y1],
    "img_width": 1280,
    "img_height": 720,
    "area_fraction": 0.1234,
    "method": "sam2.1_click",
    "score": 0.95,
    "tuning": {...}
}
```

#### Freehand Segmentation (Lines 335–465)
```python
def segment_from_freehand(
    self,
    image_url: str,
    paths: Sequence[Sequence[Tuple[float, float]]],
    mode: str = "brush",
    brush_size_px: int = 24,
    label: str = "object",
    tuning: Optional[SegmentationTuning] = None,
    sam_refine: bool = True,
) -> Dict
```

**Two Modes**:
1. **Brush Mode**: Rasterizes stroke with circular brush at each point
2. **Lasso Mode**: Fills polygon enclosed by stroke

**Refinement Pipeline** (lines 381–462):
1. **Rasterize freehand**: Convert canvas paths to binary mask
   - Function: `_rasterize_freehand_mask()` (lines 133–157)
   - Brush strokes rendered via PIL `ImageDraw.line()` with curve joints
2. **SAM2 Auto-Snap** (if `sam_refine=True`):
   - Sample positive points from drawn mask interior: `_sample_positive_points()` (lines 169–176)
   - Sample negative points from boundary ring: `_sample_negative_points()` (lines 178–209)
   - Create bounding box from mask: `_mask_prompt_box()` (lines 211–219)
   - Call SAM2 with points + box constraints
   - **Mask Selection**: Use `_pick_best_snap_mask()` (lines 221–247)
     - Scoring formula: `0.52*dice + 0.28*precision + 0.12*recall + 0.08*model_score`
3. **Fallback Handling**: Catches torchvision runtime conflicts and retry with reduced points
   - Function: `_is_sam2_torchvision_runtime_conflict()` (line 254)
   - Retry with fewer positive points (8 instead of 24)

**Output Methods**:
- `"sam2.1_auto_snap_brush"` / `"sam2.1_auto_snap_lasso"` (successful refinement)
- `"freehand_drawn_mask"` (no SAM refinement)
- `"freehand_drawn_mask_sam_fallback"` (SAM failed, use drawn only)

### Model Initialization (Lines 490–507)

```python
@lru_cache(maxsize=1)
def _sam2_predictor(config_path: str, checkpoint_path: str, device: str):
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    model = build_sam2(config_path, checkpoint_path, device=device)
    return SAM2ImagePredictor(model)
```

- **Caching**: LRU cache (maxsize=1) persists single predictor instance across calls
- **Device Handling**: CUDA or CPU detection
- **Error Handling**: Raises `SAM2UnavailableError` on torchvision mangle errors

### Threading & Thread Safety

```python
_sam2_predictor_lock = RLock()
```
- **RLock usage** (lines 272, 408, 426): Protects concurrent SAM2 predict calls
- Function wrapper: `_predict_with_set_image()` (lines 265–272)
  - Ensures image state is set before each predict
  - Implements retry on "image not set" errors

### Mask Refinement Pipeline (Lines 67–98)

```python
def refine_mask(mask_arr: np.ndarray, tuning: Optional[SegmentationTuning | InpaintTuning]) -> np.ndarray:
```

**Operations** (in order):
1. Binarize: `(mask_arr > 0).astype(np.uint8) * 255`
2. Keep largest component (if enabled): `_largest_component()` (lines 46–64)
   - Flood-fill connected components, retain largest
3. Morphological erosion: `ImageFilter.MinFilter(3)` (erosion iterations)
4. Morphological dilation: `ImageFilter.MaxFilter(3)` (dilation iterations)

**Default Tuning**:
- `dilate_px`: 0 (no dilation)
- `erode_px`: 0 (no erosion)
- `keep_largest_component`: True

---

## 2. LaMa Inpainting Implementation

### Overview
LaMa (Large Mask Inpainter) performs content-aware inpainting via subprocess execution of the LaMa repo.

**Key File**: [backend/app/capstone/inference.py](backend/app/capstone/inference.py) (Lines 508–800)

### LaMaInpainter Class

#### Status Method (Lines 522–548)

```python
def status(self) -> Dict[str, object]:
    repo = self.settings.resolved_lama_repo_path
    model = self.settings.resolved_lama_model_path
    script = (repo / "bin" / "predict.py") if repo else None
    refine_supported = bool(script and script.exists() and _lama_predict_supports_refine(str(script)))
```

**Expected Structure**:
```
external/lama/
├── bin/predict.py          (Hydra-configured inpaint script)
├── configs/
└── requirements.txt

models/
└── big-lama/               (4.3 GB checkpoint)
    ├── config.yaml
    └── checkpoint.pth
```

**Status Fields**:
- `repo_path`: Path to LaMa repository
- `model_path`: Path to model checkpoint (auto-resolves `big-lama/` subdirectory)
- `refine_supported`: Check if predict.py has `refine_predict` function
- `refiner_defaults`: Default refinement parameters

### Inpaint Pipeline (Lines 550–800)

```python
def inpaint(self, image_url: str, mask_url: str, tuning: Optional[InpaintTuning] = None) -> Dict
```

**Step 1: Load & Prepare Inputs**
```python
image = _load_image(image_url)
mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")
if mask.size != image.size:
    mask = mask.resize(image.size, Image.NEAREST)
mask_arr = np.array(mask.point(lambda px: 255 if px >= 127 else 0))
mask = Image.fromarray(refine_mask(mask_arr, tuning), mode="L")
mask_area_fraction = np.count_nonzero(mask_np) / mask_np.size
```
- Convert mask to binary (threshold at 127)
- Apply refinement from tuning config

**Step 2: Build Command for Subprocess Execution**

```python
def build_command(target_device: str, enable_refine: bool) -> List[str]:
    cmd = [
        self.settings.lama_python_executable,
        str(script_path),
        f"model.path={rel_model}",
        "indir=input",
        "outdir=output",
        "dataset.img_suffix=.png",
        f"device={target_device}",
        "hydra.run.dir=.",
        "hydra.output_subdir=null",
    ]
    if enable_refine:
        cmd.extend([
            "refine=True",
            f"refiner.gpu_ids='{refine_gpu_ids}'",
            f"refiner.modulo={refine_modulo}",
            f"refiner.n_iters={refine_n_iters}",
            f"refiner.lr={refine_lr}",
            f"refiner.min_side={refine_min_side}",
            f"refiner.max_scales={refine_max_scales}",
            f"refiner.px_budget={refine_px_budget}",
        ])
    return cmd
```

**Key Parameters**:
- `indir`: Temporary directory with `sample.png` and `sample_mask.png`
- `outdir`: Output directory for result
- Hydra config overrides for device selection

**Step 3: Refinement Decision Logic** (lines 610–638)

```
Refine Enabled If:
  ✓ tuning.enable_refinement = True
  ✓ predict.py supports refine_predict
  ✓ NOT Windows (unless CAPSTONE_LAMA_ALLOW_WINDOWS_REFINE=true)
  ✓ mask_area_fraction <= max_mask_area_fraction (default 0.35)
  ✓ device == "cuda"

Refinement Parameters (defaults):
  - gpu_ids: "0," (GPU 0)
  - modulo: 8 (refine every 8 steps)
  - n_iters: 8 (refinement iterations)
  - lr: 0.0012 (learning rate)
  - min_side: 512 (minimum side length for multiscale)
  - max_scales: 2 (number of pyramid scales)
  - px_budget: 1,400,000 (pixel budget for computation)
```

**Step 4: Subprocess Execution** (lines 670–714)

```python
completed = subprocess.run(
    command,
    cwd=str(base),
    env=env,
    capture_output=True,
    text=True,
    check=False,
)
```

- Sets `PYTHONPATH` to include LaMa repo
- Captures stdout/stderr for diagnostics
- **CUDA Failure Detection** (lines 716–740):
  - Function: `_is_lama_cuda_runtime_failure()` (lines 518–532)
  - Signatures: "tdr", "launch timed out", "cuda error", "cuda out of memory", "device-side assert"
  - Automatic fallback to CPU if CUDA failure and `lama_retry_cpu_on_cuda_failure=True`

**Output Processing** (lines 742–750)

```python
result_path = outdir / "sample.png"
if not result_path.exists():
    candidates = sorted(outdir.glob("*.png"))
    if not candidates:
        raise RuntimeError("LaMa predict completed but no output image was produced")
    result_path = candidates[0]
```

**Step 5: Result Assembly** (lines 752–800)

```python
return {
    "result_url": result_url,
    "method": "lama/big-lama",
    "refine_requested": refine_requested,
    "refine_enabled": use_refine,
    "refine_supported": refine_supported,
    "refine_skip_reason": refine_skip_reason,
    "refine_pipeline": "refine_predict" if use_refine else "predict",
    "refine_overrides": refine_overrides,
    "mask_area_fraction": round(mask_area_fraction, 6),
    "device_requested": device,
    "device_used": device_used,
    "fallback_reason": fallback_reason,
    "refiner": {...},
    "stdout_tail": completed.stdout[-500:],
    "stderr_tail": completed.stderr[-500:],
    "tuning": tuning.model_dump() if tuning else {},
}
```

### Inpaint Tuning Model

**File**: [backend/app/capstone/models.py](backend/app/capstone/models.py) (Lines 153–166)

```python
class InpaintTuning(CapstoneModel):
    mask_dilate_px: int = Field(default=4, ge=0, le=64)
    neighbor_limit: int = Field(default=5, ge=1, le=20)
    preserve_text_regions: bool = True
    enable_refinement: bool = False
    refine_gpu_ids: Optional[str] = None
    refine_modulo: Optional[int] = Field(default=None, ge=1, le=64)
    refine_n_iters: int = Field(default=8, ge=1, le=200)
    refine_lr: float = Field(default=0.0012, gt=0.0, le=0.05)
    refine_min_side: int = Field(default=512, ge=64, le=4096)
```

---

## 3. Graph Relationship Creation Logic

### Overview
Scene graphs are built from spatial relationships between bounding boxes. Relationships are computed via geometric predicates.

**Key File**: [backend/app/capstone/store.py](backend/app/capstone/store.py) (Lines 537–575)

### Graph Relationship Inference

#### Function: `infer_pair_relationships(source: BoundingBox, target: BoundingBox) -> List[Tuple[str, float]]`

**Predicates Computed** (7 total):

1. **contains** (strict spatial containment)
   - Condition: `source.x <= target.x AND source.y <= target.y AND source.x2 >= target.x2 AND source.y2 >= target.y2`
   - Function: `_contains()` (line 530)
   - Distance: Euclidean distance between box centers

2. **overlaps** (intersection area > 0)
   - Condition: `_overlap_area(source, target) > 0`
   - Function: `_overlap_area()` (line 532–535)
   - Formula: `x_overlap = max(0, min(x2_a, x2_b) - max(x_a, x_b))`
            `y_overlap = max(0, min(y2_a, y2_b) - max(y_a, y_b))`
            `area = x_overlap * y_overlap`

3. **adjacent_to** (touching but not overlapping)
   - Condition: `_overlap_area == 0 AND _distance_between_boxes <= 48px`
   - Default adjacency threshold: 48 pixels

4–7. **Directional Predicates** (based on center-to-center relationships):
   - **left_of**: `source.center_x < target.center_x` → distance = `|target.center_x - source.center_x|`
   - **right_of**: `source.center_x > target.center_x` → distance = `|target.center_x - source.center_x|`
   - **above**: `source.center_y < target.center_y` → distance = `|target.center_y - source.center_y|`
   - **below**: `source.center_y > target.center_y` → distance = `|target.center_y - source.center_y|`

#### Distance Computation

```python
def _distance_between_boxes(a: BoundingBox, b: BoundingBox) -> float:
    dx = _axis_gap(a.x, a.x2, b.x, b.x2)
    dy = _axis_gap(a.y, a.y2, b.y, b.y2)
    if dx == 0 and dy == 0:
        return 0.0
    return round(math.sqrt((dx * dx) + (dy * dy)), 2)

def _axis_gap(a0: int, a1: int, b0: int, b1: int) -> int:
    if a1 < b0:
        return b0 - a1
    if b1 < a0:
        return a0 - b1
    return 0
```

- **Axis Gap**: Returns pixel distance between box projections on an axis
  - 0 if intervals overlap
  - Positive distance if gaps exist

### Relationship Recomputation

**Method**: `_recompute_relationships()` (lines 325–341)

```python
def _recompute_relationships(self, doc: SceneDocument) -> None:
    relationships: List[SpatialRelationshipNode] = []
    objects = doc.objects
    for i, source in enumerate(objects):
        for j, target in enumerate(objects):
            if i == j:
                continue
            for predicate, distance_px in infer_pair_relationships(source.bbox, target.bbox):
                relationships.append(
                    SpatialRelationshipNode(
                        source_object_id=source.object_id,
                        target_object_id=target.object_id,
                        predicate=predicate,
                        distance_px=distance_px,
                    )
                )
    doc.spatial_relationships = relationships
```

- **Complexity**: O(n²) for n objects per scene
- **Recomputation Triggered**: On every add/remove/edit operation
- **Result Model**: [SpatialRelationshipNode](backend/app/capstone/models.py#L147–151)

### Neo4j Synchronization

**Method**: `_sync_to_neo4j()` (lines 343–465)

**Graph Schema Created**:

```
(User:CapstoneUser)-[:OWNS]->(Scene:CapstoneScene)
(Scene)-[:CONTAINS_OBJECT {layer_index}]->(ImageObject:CapstoneImageObject)
(ImageObject)-[:SPATIAL_REL {predicate, distance_px, confidence}]->(ImageObject)
(Scene)-[:CONTAINS_TEXT]->(TextRegion:CapstoneTextRegion)
(TextRegion)-[:TEXT_ON]->(ImageObject)
(TextRegion)-[:TEXT_ATTACHED_TO]->(ImageObject)
(Scene)-[:HAS_VERSION]->(CanvasVersion:CapstoneCanvasVersion)
(CanvasVersion)-[:HAS_EDIT]->(EditEvent:CapstoneEditEvent)
(EditEvent)-[:PREV_EDIT]->(EditEvent)
```

**Spatial Relationship Edge Creation** (lines 411–426):

```cypher
MATCH (src:CapstoneImageObject {object_id: $source_id})
MATCH (dst:CapstoneImageObject {object_id: $target_id})
CREATE (src)-[:SPATIAL_REL {
    rel_id: $rel_id,
    predicate: $predicate,
    confidence: $confidence,
    distance_px: $distance_px
}]->(dst)
```

---

## 4. Evaluation Metrics & Performance Tracking

### Overview
Metrics are computed at candidate and run levels. Metrics support research experiment analysis and layout/text proxy scores.

**Key File**: [backend/app/services/metric_evaluator.py](backend/app/services/metric_evaluator.py)

### MetricEvaluator Class

#### Layout Compliance Score (lines 229–273)

```python
def compute_layout_compliance_score(self, image_bytes: Optional[bytes], expected_layout: str = "centered") -> Optional[float]:
```

**Algorithm**:
1. Convert image to grayscale luminance: `arr = np.asarray(image) / 255.0`
2. Compute image gradients: `grad_y, grad_x = np.gradient(arr)`
3. Compute gradient energy: `energy = sqrt(grad_x² + grad_y²) + epsilon`
4. Compute energy-weighted centroid:
   ```
   centroid_x = sum(xx * energy) / sum(energy) / max(w-1, 1)
   centroid_y = sum(yy * energy) / sum(energy) / max(h-1, 1)
   ```
5. **Target Layout Map**:
   - `"centered"`: (0.5, 0.5)
   - `"left"` / `"left_focus"`: (0.35, 0.5)
   - `"right"` / `"right_focus"`: (0.65, 0.5)
   - `"top"`: (0.5, 0.35)
   - `"bottom"`: (0.5, 0.65)
6. **Score Computation**:
   ```
   distance = sqrt((centroid_x - target_x)² + (centroid_y - target_y)²)
   normalized_distance = distance / sqrt(2.0)
   score = 1.0 - (1.35 * normalized_distance)
   return clamp(score, 0.0, 1.0)
   ```

**Output**: Float in [0, 1] (higher is better; centered layouts get 1.0)

#### Text Legibility Score (lines 275–313)

```python
def compute_text_legibility_score(self, image_bytes: Optional[bytes], text_position: str = "bottom") -> Optional[float]:
```

**Algorithm**:
1. Extract text region based on position:
   - `"top"`: top 1/3 of image
   - `"center"`: middle 1/3
   - `"bottom"`: bottom 1/3
2. Compute local contrast metrics:
   ```
   p95 = 95th percentile of region luminance
   p5 = 5th percentile
   contrast = p95 - p5
   std_dev = standard deviation of region
   ```
3. **Score Blending**:
   ```
   score = (0.70 * contrast) + (0.60 * std_dev)
   return clamp(score, 0.0, 1.0)
   ```

**Output**: Float in [0, 1] (higher indicates better text region definition)

#### Color Extraction (lines 163–172)

```python
def extract_colors_from_image_bytes(self, image_bytes: Optional[bytes], max_colors: int = 5) -> List[str]:
    colors = extract_colors_from_image(image_bytes, color_count=max_colors)
    return [c.get("hex", "") for c in colors if c.get("hex")]
```

- Integrates with `app.scraping.color_extractor`
- Returns hex color codes (e.g., `"#FF6A4D"`)

#### Delta-E 2000 Color Distance (lines 74–154)

Implements full **CIEDE2000** color distance metric:
- RGB → sRGB linear → XYZ (D65 white point) → Lab color space
- Computes parametric weighting factors (S_L, S_C, S_H)
- Final delta-E formula with rotation term

**Use Case**: Brand color compliance evaluation

### Accuracy Presets API

**Endpoint**: `GET /api/v3/accuracy-presets`  
**File**: [backend/app/routers/v3_capstone.py](backend/app/routers/v3_capstone.py) (Lines 46–85)

```python
@router.get("/accuracy-presets")
def get_accuracy_presets():
    return {
        "segmentation": {
            "balanced": SegmentationTuning().model_dump(),
            "tight_edges": SegmentationTuning(dilate_px=0, erode_px=1, min_area_fraction=0.0005).model_dump(),
            "object_recall": SegmentationTuning(
                multimask_strategy="largest_mask",
                dilate_px=2,
                erode_px=0,
                min_area_fraction=0.002,
            ).model_dump(),
        },
        "inpainting": {
            "balanced": InpaintTuning().model_dump(),
            "background_cleanup": InpaintTuning(mask_dilate_px=8, neighbor_limit=6).model_dump(),
            "detail_preserve": InpaintTuning(mask_dilate_px=2, neighbor_limit=4).model_dump(),
            "refine_soft": InpaintTuning(
                mask_dilate_px=2,
                neighbor_limit=5,
                enable_refinement=True,
                refine_n_iters=6,
                refine_lr=0.001,
                refine_max_scales=2,
                refine_px_budget=1200000,
            ).model_dump(),
            "hq_refine": InpaintTuning(
                mask_dilate_px=3,
                neighbor_limit=5,
                enable_refinement=True,
                refine_n_iters=10,
                refine_lr=0.0012,
                refine_max_scales=2,
                refine_px_budget=1400000,
            ).model_dump(),
        },
    }
```

**Preset Categories**:

| Preset | Use Case | Key Parameters |
|--------|----------|-----------------|
| **segmentation.balanced** | Default | dilate=0, erode=0, min_area=0.1% |
| **segmentation.tight_edges** | Precise contours | erode=1, min_area=0.05% |
| **segmentation.object_recall** | Large/small objects | largest_mask, dilate=2, min_area=0.2% |
| **inpainting.balanced** | Default | dilate=4px, neighbors=5 |
| **inpainting.background_cleanup** | Remove backgrounds | dilate=8px, neighbors=6 |
| **inpainting.detail_preserve** | Fine details | dilate=2px, neighbors=4 |
| **inpainting.refine_soft** | Quick refinement | refine_iters=6, budget=1.2M px |
| **inpainting.hq_refine** | High quality | refine_iters=10, budget=1.4M px |

---

## 5. Test Data & Evaluation Test Suite

### Test Files

#### [tests/capstone/test_capstone_store.py](tests/capstone/test_capstone_store.py)

**Key Tests**:

1. `test_infer_pair_relationships_captures_overlap_and_direction()` (lines 8–14)
   - Validates relationship inference
   - Example: Left box overlaps right box → captures both "overlaps" and "left_of"

2. `test_capstone_store_creates_init_history_and_context()` (lines 17–55)
   - Full workflow: create scene → add objects → add text → query neighbors
   - Validates edit event chain and spatial relationship computation

3. `test_capstone_store_remove_object_updates_history()` (lines 58–79)
   - Tests object removal with graph cleanup
   - Verifies edit event type and canvas version marking

#### [tests/capstone/test_capstone_api.py](tests/capstone/test_capstone_api.py)

1. `test_capstone_upload_and_remove_flow_with_mocked_models()` (lines 17–115)
   - **Workflow**: Upload → Segment (mock) → Remove Object → Verify inpaint tuning
   - **Mocked Components**: SAM2 segmenter, LaMa inpainter
   - **Assertions**:
     - Checks `refine_requested`, `refine_enabled`, `refine_pipeline` flags
     - Validates refine_overrides contain `"refine=True"`
     - Verifies mask_area_fraction and refiner parameters are passed through

2. `test_accuracy_presets_endpoint()` (lines 117–125)
   - Validates /api/v3/accuracy-presets endpoint
   - Checks for presets in segmentation and inpainting categories

3. `test_capstone_freehand_segmentation_registers_object()` (lines 127–180)
   - Tests freehand brush mode with SAM refinement
   - **Mock paths**: 3-point brush stroke (x,y normalized)

#### [tests/interaction/test_graph_conditioning.py](tests/interaction/test_graph_conditioning.py) – MetricEvaluator Tests (lines 86–120)

```python
class MetricEvaluatorProxyTests(unittest.TestCase):
    def test_layout_and_text_proxy_scores_exist(self):
        layout_score = self.evaluator.compute_layout_compliance_score(
            self.image_bytes, expected_layout="centered"
        )
        text_score = self.evaluator.compute_text_legibility_score(
            self.image_bytes, text_position="bottom"
        )
        self.assertIsNotNone(layout_score)
        self.assertIsNotNone(text_score)
        self.assertGreaterEqual(layout_score, 0.0)
        self.assertLessEqual(layout_score, 1.0)
```

- Generates test image with centered subject + bottom stripe
- Validates proxy metrics return valid float ranges [0, 1]

### Test Data Generation

**File**: `tests/interaction/test_graph_conditioning.py` (lines 10–27)

```python
def _make_test_image_bytes(size: int = 192) -> bytes:
    image = Image.new("RGB", (size, size), color=(38, 44, 60))
    draw = ImageDraw.Draw(image)

    # Brighter centered subject region for layout proxy.
    subject_size = int(size * 0.45)
    start = (size - subject_size) // 2
    end = start + subject_size
    draw.rectangle((start, start, end, end), fill=(208, 122, 92))

    # Bottom stripe to create a text-zone contrast signal.
    stripe_top = int(size * 0.72)
    draw.rectangle((0, stripe_top, size, size), fill=(245, 245, 245))

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
```

**Image Properties**:
- 192×192 RGB, dark background (38, 44, 60)
- 45% centered bright rectangle (208, 122, 92) for layout signal
- 28% bottom bright stripe (245, 245, 245) for text signal

---

## 6. Configuration & Runtime Settings

### Main Configuration

**File**: [backend/app/config.py](backend/app/config.py)

```python
class Settings(BaseSettings):
    # Application
    app_name: str = "Brand-Aligned Content Generation Platform"
    debug: bool = False
    
    # Neo4j Aura
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    
    # Capstone Models
    allow_google_image_models: bool = False
    allow_openrouter_image_models: bool = True
    image_provider_priority: str = "openrouter,replicate,fal.ai"
```

### Capstone Runtime Settings

**File**: [backend/app/capstone/runtime.py](backend/app/capstone/runtime.py) (Lines 22–45)

```python
class CapstoneRuntimeSettings(BaseModel):
    # SAM2
    sam2_checkpoint: Path = Path("checkpoints/sam2.1_hiera_large.pt")
    sam2_config: str = "configs/sam2.1/sam2.1_hiera_l.yaml"
    
    # LaMa
    lama_repo_path: Optional[Path] = None
    lama_model_path: Optional[Path] = None
    lama_python_executable: str = sys.executable
    
    # Refinement
    lama_refiner_gpu_ids: str = "0,"
    lama_refiner_modulo: int = 8
    lama_refiner_n_iters: int = 8
    lama_refiner_lr: float = 0.0012
    lama_refiner_min_side: int = 512
    lama_refiner_max_scales: int = 2
    lama_refiner_px_budget: int = 1400000
    lama_refiner_max_mask_area_fraction: float = 0.35
    
    # Device
    device_preference: Literal["auto", "cuda", "cpu"] = "auto"
    
    # Fallbacks
    allow_mock_fallbacks: bool = False
    lama_allow_windows_refine: bool = False
    lama_retry_cpu_on_cuda_failure: bool = True
```

**Environment Variable Mappings**:
- `CAPSTONE_SAM2_CHECKPOINT`: Path to checkpoint
- `CAPSTONE_SAM2_CONFIG`: Path to config
- `CAPSTONE_LAMA_REPO_PATH`: Path to LaMa repo
- `CAPSTONE_LAMA_MODEL_PATH`: Path to model
- `CAPSTONE_LAMA_REFINER_*`: Refinement parameters
- `CAPSTONE_DEVICE`: "auto", "cuda", or "cpu"
- `CAPSTONE_ALLOW_MOCK_FALLBACKS`: Enable ellipse mock when SAM2 unavailable

---

## 7. Performance & Benchmarking Infrastructure

### VRAM Profiling Template

**File**: [docs/vram_profile_report.md](docs/vram_profile_report.md)

**Measurement Matrix** (Section 4):

```
| run_id | method | resolution | steps | precision | adapters | batch_size |
|--------|--------|------------|-------|-----------|----------|-----------|
| R01    | prompt_only | 768 | 30 | fp16 | none | 1 |
| R02    | retrieval_prompt | 768 | 30 | fp16 | none | 1 |
| R03    | adapter_control | 768 | 30 | fp16 | control_stack_v1 | 1 |
| R04    | graph_guided | 768 | 30 | fp16 | control_stack_v1 | 1 |
| R05    | graph_guided | 1024 | 30 | fp16 | control_stack_v1 | 1 |
```

**Metrics Captured per Run**:
1. `peak_vram_gb` (max memory used)
2. `avg_vram_gb` (average over run)
3. `avg_step_ms` (per-step latency)
4. `total_latency_s` (end-to-end time)
5. `oom_event` (out-of-memory boolean)
6. `quality_proxy_score` (optional metric)

**Acceptance Criteria**:
- Peak VRAM ≤ 11.5 GB (RTX 5070 Ti: 12 GB total)
- No OOM for primary production config
- Bounded runtime variation across repeats

**Fallback Policy** (Section 8):
1. Reduce resolution
2. Reduce concurrent adapters
3. Switch from dense to sparse decode
4. Reduce guidance update frequency

### Research Metrics (Backend)

**File**: [backend/tests/test_research_smoke.py](backend/tests/test_research_smoke.py)

**Metrics Aggregation** (lines 104–109):

```python
rows = [
    {"run_id": "run_1", "method_name": "prompt_only", "metrics": {"seed": 11, "brand_score": 0.40}},
    {"run_id": "run_1", "method_name": "prompt_only", "metrics": {"seed": 22, "brand_score": 0.45}},
    {"run_id": "run_2", "method_name": "graph_guided", "metrics": {"seed": 11, "brand_score": 0.62}},
    {"run_id": "run_2", "method_name": "graph_guided", "metrics": {"seed": 22, "brand_score": 0.66}},
]
```

**Tracked Metrics**:
- `seed`: Random seed for reproducibility
- `brand_score`: Brand alignment score (likely 0–1 normalized)

### Experiment Configuration Templates

**File**: [experiments/configs/capstone_accuracy_profile.template.json](experiments/configs/capstone_accuracy_profile.template.json)

```json
{
  "name": "patterned-floor-object-removal",
  "scene_id": "replace-me",
  "object_id": "replace-me",
  "segmentation_tuning": {
    "multimask_strategy": "largest_mask",
    "dilate_px": 2,
    "erode_px": 0,
    "keep_largest_component": true,
    "min_area_fraction": 0.002
  },
  "inpaint_tuning": {
    "mask_dilate_px": 8,
    "neighbor_limit": 6,
    "preserve_text_regions": true
  },
  "notes": [
    "Use when SAM slightly under-covers the object silhouette.",
    "Compare against the balanced preset and log visible halo reduction."
  ]
}
```

---

## 8. API Endpoints Summary

### Scene Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v3/scenes/upload` | POST | Upload image → create scene |
| `/api/v3/scenes` | POST | Create scene from path |
| `/api/v3/scenes/{scene_id}` | GET | Fetch scene document |
| `/api/v3/scenes/{scene_id}/history` | GET | Edit event chain |
| `/api/v3/scenes/{scene_id}/inpaint-context/{object_id}` | GET | Get neighbors for inpainting |

### Segmentation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v3/scenes/{scene_id}/segment-click` | POST | Point-to-mask SAM2 |
| `/api/v3/scenes/{scene_id}/segment-freehand` | POST | Brush/lasso → SAM refine |

### Object Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v3/scenes/{scene_id}/objects` | POST | Add object to scene |
| `/api/v3/scenes/{scene_id}/remove-object` | POST | Segment + inpaint + remove |
| `/api/v3/scenes/{scene_id}/text-regions` | POST | Add text region |
| `/api/v3/scenes/{scene_id}/edits` | POST | Record edit event |
| `/api/v3/scenes/{scene_id}/aspect-ratio` | POST | Update canvas dimensions |

### Metadata

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v3/capabilities` | GET | SAM2/LaMa status |
| `/api/v3/accuracy-presets` | GET | Segmentation/inpainting presets |

---

## 9. Key Implementation Notes

### Threading & Concurrency

- **SAM2 Lock** (`RLock`): Protects simultaneous SAM2 predictor access
- **LaMa Subprocess**: Single process per call; no concurrent LaMa runs in current design

### Fallback Mechanisms

1. **SAM2 Click**:
   - If unavailable and `allow_mock_fallbacks=True`: Return mock ellipse
   - If SAM predictor fails: Raise `SAM2UnavailableError` → HTTP 503

2. **SAM2 Freehand**:
   - If SAM initialization fails: Fall back to drawn mask only
   - If SAM predict fails: Retry with reduced point count (8 → 24)
   - If retry fails: Use drawn mask as-is

3. **LaMa Inpaint**:
   - If CUDA runtime failure detected: Auto-retry on CPU
   - If CPU retry fails: Raise `LaMaUnavailableError` → HTTP 503

### Mask Refinement

- **Binarization**: Threshold at 0 (any positive value → 255)
- **Connected Components**: Flood-fill to find largest cluster
- **Erosion/Dilation**: PIL `ImageFilter.MinFilter()` / `ImageFilter.MaxFilter()`

### Graph Synchronization

- **Primary Storage**: JSON files in `uploads/capstone/scenes/`
- **Secondary Storage**: Neo4j (optional sync; failures do not break JSON store)
- **Relationship Recomputation**: O(n²) but typically n < 50 objects per scene

### Device Management

```python
def resolve_device(preference: str) -> str:
    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return "cuda"
    if has_torch():
        import torch
        if torch.cuda.is_available():
            return "cuda"
    return "cpu"
```

- Auto-detects CUDA availability if preference = "auto"

---

## 10. Known Constraints & Limitations

| Constraint | Value | Reason |
|-----------|-------|--------|
| Max objects per scene | ~500 | O(n²) relationship computation |
| Max segmentation masks | 3 (multimask) | SAM2 output fixed at 3 candidates |
| SAM2 LRU cache | 1 predictor | Prevents memory bloat; reuses instance |
| Adjacency threshold | 48 px | Heuristic for "touching" semantics |
| LaMa mask area max | 35% | Windows TDR + GPU memory safety |
| Default refinement iters | 8 | Balance quality vs. latency |
| Refinement GPU IDs | "0," | Single-GPU assumption |

---

## 11. Integration Points

### To Capstone Workflows

- **Scene Upload**: Entrypoint for image → scene creation
- **Segment & Register**: Segment object → store in scene graph → sync to Neo4j
- **Remove Object**: Query context neighbors → inpaint → update graph → record edit
- **Edit History**: Linear event chain for undo/redo

### To Research Pipeline

- **Metric Evaluator**: Layout/text proxy scores for candidate evaluation
- **Run Aggregation**: Collect brand_score metrics per seed → compute statistics
- **Experiment Config**: Store test cases with tuning presets

---

## Appendix: Code Locations

### Primary Implementation Files

| Component | File | Lines |
|-----------|------|-------|
| SAM2 Segmentation | backend/app/capstone/inference.py | 1–507 |
| LaMa Inpainting | backend/app/capstone/inference.py | 508–800 |
| Graph Store | backend/app/capstone/store.py | 1–575 |
| Models/Schema | backend/app/capstone/models.py | 1–200+ |
| Runtime Settings | backend/app/capstone/runtime.py | 1–150 |
| API Endpoints | backend/app/routers/v3_capstone.py | 1–400+ |
| Metrics | backend/app/services/metric_evaluator.py | 1–300+ |

### Test Files

| Test | File | Coverage |
|------|------|----------|
| Graph Relations | tests/capstone/test_capstone_store.py | Inference & storage |
| API Integration | tests/capstone/test_capstone_api.py | HTTP flows |
| Metrics | tests/interaction/test_graph_conditioning.py | Layout/text scores |

### Configuration Templates

| Config | File |
|--------|------|
| Accuracy Presets | experiments/configs/capstone_accuracy_profile.template.json |
| Research Runs | experiments/configs/research_run_config.template.json |
| VRAM Profile | docs/vram_profile_report.md |

