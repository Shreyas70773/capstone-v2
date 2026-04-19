# Capstone V3: Testing Strategy & Validation

**Version:** 3.0.0  
**Audience:** QA Engineers, Backend Developers  
**Purpose:** Comprehensive testing approach for V3 system

---

## 🧪 Testing Pyramid

```
        ╱╲
       ╱  ╲         E2E Tests (Few)
      ╱────╲        • Full user workflows
     ╱      ╲       • Real ML models
    ╱────────╲
   ╱          ╲     Integration Tests (Some)
  ╱────────────╲    • API + Store + Inference
 ╱              ╲   • Scene state transitions
╱────────────────╲
                    Unit Tests (Many)
                    • Models, utilities
                    • SAM2/LaMa wrappers
                    • Spatial relationships
```

---

## 📋 Test Categories

### 1. Unit Tests (Model Layer)

**Location:** `backend/tests/capstone/`

```python
# test_models.py
def test_scene_node_creation():
    """Test SceneNode initialization."""
    scene = SceneNode(
        image_path="https://s3.../image.png",
        canvas_width=1920,
        canvas_height=1080,
        aspect_ratio="16:9",
        owner_user_id="test_user"
    )
    assert scene.scene_id.startswith("scene_")
    assert scene.schema_version == "3.0.0"
    assert scene.canvas_width == 1920

def test_bounding_box_properties():
    """Test BoundingBox computed properties."""
    bbox = BoundingBox(x=100, y=200, w=300, h=400)
    assert bbox.x2 == 400
    assert bbox.y2 == 600
    assert bbox.center_x == 250
    assert bbox.center_y == 400

def test_spatial_relationship_computation():
    """Test spatial relationship inference."""
    obj1 = ImageObjectNode(class_label="sofa", bbox=BoundingBox(x=0, y=0, w=600, h=400))
    obj2 = ImageObjectNode(class_label="lamp", bbox=BoundingBox(x=700, y=50, w=100, h=150))
    
    # obj2 is to the right of obj1
    rel = infer_relationship(obj1, obj2)
    assert rel.predicate == "right_of"
    assert rel.source_object_id == obj1.object_id

def test_edit_event_immutability():
    """EditEvents should not be modified after creation."""
    event = EditEventNode(
        event_type="REMOVE_OBJECT",
        delta_json={"removed": "obj_123"}
    )
    # Attempting to modify should raise or be prevented
    with pytest.raises(Exception):
        event.event_type = "MODIFIED"

def test_segmentation_tuning_validation():
    """Test SegmentationTuning bounds."""
    # Valid tuning
    tuning = SegmentationTuning(dilate_px=5, erode_px=3)
    assert tuning.dilate_px == 5
    
    # Invalid tuning should raise ValidationError
    with pytest.raises(ValueError):
        SegmentationTuning(dilate_px=100)  # Max 64
    
    with pytest.raises(ValueError):
        SegmentationTuning(min_area_fraction=1.5)  # Max 1.0

# test_inference_wrappers.py
def test_sam2_segmenter_status():
    """Test SAM2 status reporting."""
    segmenter = SAM2Segmenter()
    status = segmenter.status()
    assert "ready" in status
    assert "device" in status
    assert status["model_name"] == "sam2.1_hiera_large"

def test_lama_inpainter_status():
    """Test LaMa status reporting."""
    inpainter = LaMaInpainter()
    status = inpainter.status()
    assert "ready" in status
    assert "version" in status

def test_mask_refinement_dilate():
    """Test mask dilation operation."""
    # Create simple cross-shaped mask
    mask = np.zeros((10, 10), dtype=np.uint8)
    mask[5, :] = 255  # Horizontal line
    mask[:, 5] = 255  # Vertical line
    
    tuning = SegmentationTuning(dilate_px=1, erode_px=0)
    refined = refine_mask(mask, tuning)
    
    # After dilation, mask should be larger
    assert np.count_nonzero(refined) > np.count_nonzero(mask)

def test_mask_refinement_erode():
    """Test mask erosion operation."""
    # Create filled square
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2:18, 2:18] = 255
    
    tuning = SegmentationTuning(dilate_px=0, erode_px=1)
    refined = refine_mask(mask, tuning)
    
    # After erosion, mask should be smaller
    assert np.count_nonzero(refined) < np.count_nonzero(mask)
```

**Run unit tests:**
```bash
cd backend
pytest tests/capstone/test_models.py -v
pytest tests/capstone/test_inference_wrappers.py -v
```

---

### 2. Integration Tests (API + Store + Inference)

**Location:** `backend/tests/capstone/`

```python
# test_integration_scene_workflow.py
@pytest.fixture
def api_client():
    """Create test FastAPI client."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_complete_workflow(api_client, tmp_path):
    """Test full workflow: upload → segment → remove."""
    
    # Step 1: Upload image
    test_image_path = Path(__file__).parent / "fixtures" / "test_sofa.png"
    with open(test_image_path, "rb") as f:
        response = api_client.post(
            "/api/v3/scenes/upload",
            files={"file": ("test.png", f, "image/png")},
            data={"title": "Test Scene"}
        )
    
    assert response.status_code == 200
    scene_data = response.json()
    scene_id = scene_data["scene_id"]
    
    # Step 2: Get scene state
    response = api_client.get(f"/api/v3/scenes/{scene_id}")
    assert response.status_code == 200
    scene = response.json()
    assert scene["scene"]["scene_id"] == scene_id
    assert len(scene["objects"]) == 0  # No objects yet
    
    # Step 3: Segment click
    response = api_client.post(
        f"/api/v3/scenes/{scene_id}/segment-click",
        json={
            "click_x": 0.5,
            "click_y": 0.5,
            "label": "sofa",
            "confidence": 1.0,
            "register_object": True
        }
    )
    
    if response.status_code == 200:  # Only if SAM2 available
        segmentation = response.json()
        object_id = segmentation["object_id"]
        
        # Step 4: Verify object registered
        response = api_client.get(f"/api/v3/scenes/{scene_id}")
        scene = response.json()
        assert len(scene["objects"]) == 1
        assert scene["objects"][0]["object_id"] == object_id
        
        # Step 5: Remove object
        response = api_client.post(
            f"/api/v3/scenes/{scene_id}/remove-object",
            json={
                "object_id": object_id,
                "record_event": True
            }
        )
        
        if response.status_code == 200:  # Only if LaMa available
            result = response.json()
            assert "new_canvas_image_url" in result
            assert "edit_event_id" in result
            
            # Step 6: Verify object removed
            response = api_client.get(f"/api/v3/scenes/{scene_id}")
            scene = response.json()
            assert len(scene["objects"]) == 0
            assert len(scene["edit_events"]) == 2  # INIT + REMOVE_OBJECT

def test_spatial_relationships_update(api_client):
    """Test spatial relationships are recomputed after edits."""
    
    # Create scene with 2 objects
    response = api_client.post("/api/v3/scenes", json={...})
    scene_id = response.json()["scene_id"]
    
    # Add object 1
    api_client.post(f"/api/v3/scenes/{scene_id}/objects", json={
        "class_label": "chair",
        "bbox": {"x": 0, "y": 0, "w": 100, "h": 100}
    })
    
    # Add object 2 (to the right of object 1)
    api_client.post(f"/api/v3/scenes/{scene_id}/objects", json={
        "class_label": "table",
        "bbox": {"x": 150, "y": 0, "w": 100, "h": 100}
    })
    
    # Get scene and verify relationships
    response = api_client.get(f"/api/v3/scenes/{scene_id}")
    scene = response.json()
    
    assert len(scene["spatial_relationships"]) > 0
    chair_rels = [r for r in scene["spatial_relationships"] 
                   if scene["objects"][0]["object_id"] in (r["source_object_id"], r["target_object_id"])]
    
    # Verify relationship type
    right_of_rels = [r for r in chair_rels if r["predicate"] == "right_of"]
    assert len(right_of_rels) >= 1
```

**Run integration tests:**
```bash
cd backend
pytest tests/capstone/test_integration_scene_workflow.py -v -s
```

---

### 3. ML Validation Tests

**Location:** `backend/tests/capstone/`

```python
# test_ml_quality.py
def test_sam2_segmentation_quality():
    """Test SAM2 produces reasonable segmentation masks."""
    if not has_sam2():
        pytest.skip("SAM2 not available")
    
    segmenter = SAM2Segmenter()
    
    # Load test image with known object
    image_path = "tests/fixtures/clear_object.png"
    
    # Click in center of object
    result = segmenter.segment_from_point(image_path, click_x=0.5, click_y=0.5)
    
    # Assertions
    assert result["area_fraction"] > 0.05  # Segmented something substantial
    assert result["area_fraction"] < 0.95  # Not entire image
    assert result["confidence"] > 0.5      # Reasonable confidence

def test_lama_inpainting_preserves_boundaries():
    """Test LaMa inpainting doesn't corrupt image boundaries."""
    if not has_lama():
        pytest.skip("LaMa not available")
    
    inpainter = LaMaInpainter()
    
    # Load test image and mask
    image_url = "s3://test-images/scene.png"
    mask_url = "s3://test-masks/object.png"
    
    inpainted_url = inpainter.inpaint(image_url, mask_url, {})
    
    # Load result and verify
    result_image = Image.open(io.BytesIO(fetch_image_bytes(inpainted_url)))
    original = Image.open(io.BytesIO(fetch_image_bytes(image_url)))
    
    # Boundaries should match
    assert result_image.size == original.size
    
    # Non-mask regions should be similar
    # (pixel-level comparison would be too strict)
```

---

### 4. E2E Tests (User Workflows)

**Location:** `frontend/tests/e2e/`

```javascript
// capstone_workflow.spec.ts (Playwright)
import { test, expect } from '@playwright/test';

test('Complete V3 workflow: upload → segment → remove', async ({ page }) => {
  // Navigate to Capstone Studio
  await page.goto('http://localhost:5173/capstone-studio');
  await expect(page).toHaveTitle(/Capstone Studio/i);
  
  // Step 1: Upload image
  const uploadButton = page.locator('button:has-text("Upload Image")');
  await uploadButton.click();
  
  // Fill upload modal
  await page.setInputFiles('input[type="file"]', 'tests/fixtures/sofa.png');
  await page.locator('input[name="title"]').fill('Test Scene');
  await page.locator('button:has-text("Upload")').click();
  
  // Wait for canvas to load
  await page.waitForSelector('canvas');
  await expect(page.locator('text=No image loaded')).not.toBeVisible();
  
  // Step 2: Click to segment
  const canvas = page.locator('canvas');
  await canvas.click({ position: { x: 300, y: 300 } });
  
  // Wait for mask overlay
  await page.waitForTimeout(3000);
  
  // Step 3: Remove object
  const removeButton = page.locator('button:has-text("Remove Object")');
  await expect(removeButton).toBeVisible();
  await removeButton.click();
  
  // Wait for inpainting
  await page.waitForTimeout(8000);
  
  // Step 4: Verify result
  const historyButton = page.locator('button:has-text("Show History")');
  await historyButton.click();
  
  // Check history panel shows edit events
  const historyPanel = page.locator('[class*="history"]');
  await expect(historyPanel).toContainText('REMOVE_OBJECT');
});

test('Accuracy preset selection', async ({ page }) => {
  await page.goto('http://localhost:5173/capstone-studio');
  
  // Upload image
  await page.locator('button:has-text("Upload Image")').click();
  await page.setInputFiles('input[type="file"]', 'tests/fixtures/sofa.png');
  await page.locator('button:has-text("Upload")').click();
  await page.waitForSelector('canvas');
  
  // Change accuracy preset
  const presetSelect = page.locator('select');
  await presetSelect.selectOption('tight_edges');
  
  // Verify preset changed
  const currentValue = await presetSelect.inputValue();
  expect(currentValue).toBe('tight_edges');
});
```

**Run E2E tests:**
```bash
cd frontend
npx playwright test tests/e2e/capstone_workflow.spec.ts
```

---

## ✅ Test Coverage Requirements

| Component | Target | Current |
|-----------|--------|---------|
| Models (Pydantic) | 95%+ | 80% |
| Inference wrappers | 85%+ | 70% |
| Scene Store (JSON/Neo4j) | 90%+ | 75% |
| API endpoints | 80%+ | 60% |
| Frontend components | 70%+ | 50% |
| **Overall** | **80%+** | **~65%** |

**View coverage:**
```bash
cd backend
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 🔄 Continuous Integration (CI)

**GitHub Actions workflow:** `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt -r requirements_capstone_v3.txt
          pip install git+https://github.com/facebookresearch/sam2.git
      
      - name: Run unit tests
        run: |
          cd backend
          pytest tests/capstone/test_models.py -v
      
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/capstone/test_integration_scene_workflow.py -v

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: cd frontend && npm install
      
      - name: Build
        run: cd frontend && npm run build
      
      - name: Run tests
        run: cd frontend && npm run test:unit

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Start backend
        run: cd backend && python run_server.py &
      
      - name: Start frontend
        run: cd frontend && npm run dev &
      
      - name: Wait for services
        run: sleep 10
      
      - name: Run E2E tests
        run: cd frontend && npx playwright test
```

---

## 🧩 Test Fixtures

**Location:** `backend/tests/fixtures/`

```python
# conftest.py
@pytest.fixture
def sample_image():
    """Create 100x100 RGB test image."""
    img = Image.new('RGB', (100, 100), color='blue')
    return img

@pytest.fixture
def sample_mask():
    """Create binary mask."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 255  # Square in center
    return mask

@pytest.fixture
def sample_scene_document():
    """Create sample SceneDocument."""
    return SceneDocument(
        user=UserNode(user_id="test_user"),
        scene=SceneNode(
            image_path="https://s3.../image.png",
            canvas_width=100,
            canvas_height=100,
            aspect_ratio="1:1",
            owner_user_id="test_user"
        ),
        objects=[
            ImageObjectNode(
                class_label="chair",
                confidence=0.95,
                bbox=BoundingBox(x=10, y=10, w=30, h=40)
            )
        ]
    )
```

---

## 📊 Performance Benchmarks

**Location:** `backend/tests/capstone/test_performance.py`

```python
# test_performance.py
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

def test_spatial_relationships_computation_performance(
    benchmark: BenchmarkFixture,
    sample_scene_document
):
    """Benchmark spatial relationship computation."""
    def compute_rels():
        return compute_spatial_relationships(sample_scene_document.objects)
    
    result = benchmark(compute_rels)
    assert len(result) > 0

def test_scene_serialization_performance(benchmark):
    """Benchmark JSON serialization."""
    scene = sample_scene_document()
    
    def serialize():
        return scene.model_dump_json()
    
    result = benchmark(serialize)
    assert len(result) > 0

# Run with: pytest tests/capstone/test_performance.py --benchmark-only
```

---

## 🎯 Test Execution Checklist

```bash
# Unit tests (fast, isolated)
pytest backend/tests/capstone/test_models.py -v

# Integration tests (medium speed)
pytest backend/tests/capstone/test_integration_scene_workflow.py -v

# ML validation (slow, GPU required)
pytest backend/tests/capstone/test_ml_quality.py -v

# Performance benchmarks
pytest backend/tests/capstone/test_performance.py --benchmark-only

# Frontend unit tests
cd frontend && npm run test:unit

# E2E tests (slowest, full stack)
cd frontend && npx playwright test

# Coverage report
cd backend && pytest --cov=app --cov-report=html

# All tests with CI
pytest backend/tests/ && cd frontend && npm run test && npx playwright test
```

---

## 📈 Metrics to Track

```
Backend Metrics:
├─ Test coverage (target: 80%+)
├─ Passing tests (target: 100%)
├─ SAM2 inference latency (target: <2s)
├─ LaMa inpainting latency (target: <10s)
└─ API response time (target: <500ms)

Frontend Metrics:
├─ Test coverage (target: 70%+)
├─ Build time (target: <30s)
├─ Bundle size (target: <500KB gzipped)
└─ Core Web Vitals (Lighthouse)

System Metrics:
├─ Uptime (target: 99%+)
├─ Error rate (target: <0.1%)
└─ VRAM usage (target: <14GB)
```

---

**Next:** Refer back to [00_SYSTEM_OVERVIEW_V3.md](./00_SYSTEM_OVERVIEW_V3.md) for the complete picture.
