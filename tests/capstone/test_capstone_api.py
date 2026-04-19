from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.capstone.store import capstone_scene_store
from app.main import app


client = TestClient(app)


def _make_png(path: Path, color=(240, 240, 240), size=(256, 256)) -> Path:
    Image.new("RGB", size, color).save(path, format="PNG")
    return path


def test_capstone_upload_and_remove_flow_with_mocked_models(tmp_path, monkeypatch):
    capstone_scene_store.root = tmp_path / "scenes"
    capstone_scene_store.root.mkdir(parents=True, exist_ok=True)

    upload_bytes = io.BytesIO()
    Image.new("RGB", (256, 256), (245, 245, 245)).save(upload_bytes, format="PNG")
    upload_bytes.seek(0)

    upload_resp = client.post(
        "/api/v3/scenes/upload",
        files={"file": ("scene.png", upload_bytes.getvalue(), "image/png")},
        data={"title": "Test Scene"},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    scene = upload_resp.json()
    scene_id = scene["scene"]["scene_id"]

    mask_path = _make_png(tmp_path / "mask.png", color=(255, 255, 255))
    result_path = _make_png(tmp_path / "result.png", color=(220, 220, 220))
    seen_inpaint_tuning: dict[str, object] = {}

    def _fake_segment(image_url, click_x, click_y, label, tuning=None):  # noqa: ARG001
        return {
            "mask_url": str(mask_path),
            "bbox": [40, 60, 140, 180],
            "img_width": 256,
            "img_height": 256,
            "area_fraction": 0.1,
            "method": "sam2.1_click",
            "score": 0.98,
            "tuning": tuning.model_dump() if tuning else {},
        }

    def _fake_inpaint(image_url, mask_url, tuning=None):  # noqa: ARG001
        nonlocal seen_inpaint_tuning
        seen_inpaint_tuning = tuning.model_dump() if tuning else {}
        return {
            "result_url": str(result_path),
            "method": "lama/big-lama",
            "refine_requested": bool(tuning and tuning.enable_refinement),
            "refine_enabled": bool(tuning and tuning.enable_refinement),
            "refine_supported": True,
            "refine_skip_reason": "",
            "refine_pipeline": "refine_predict" if (tuning and tuning.enable_refinement) else "predict",
            "refine_overrides": ["refine=True"],
            "mask_area_fraction": 0.12,
            "refiner": {
                "n_iters": tuning.refine_n_iters if tuning else 15,
            },
            "tuning": tuning.model_dump() if tuning else {},
        }

    monkeypatch.setattr("app.routers.v3_capstone.sam2_segmenter.segment_from_click", _fake_segment)
    monkeypatch.setattr("app.routers.v3_capstone.lama_inpainter.inpaint", _fake_inpaint)

    segment_resp = client.post(
        f"/api/v3/scenes/{scene_id}/segment-click",
        json={
            "click_x": 0.5,
            "click_y": 0.5,
            "label": "chair",
            "tuning": {"multimask_strategy": "largest_mask", "dilate_px": 2},
        },
    )
    assert segment_resp.status_code == 200, segment_resp.text
    object_id = segment_resp.json()["scene_object_id"]

    remove_resp = client.post(
        f"/api/v3/scenes/{scene_id}/remove-object",
        json={
            "object_id": object_id,
            "tuning": {
                "mask_dilate_px": 8,
                "neighbor_limit": 6,
                "enable_refinement": True,
                "refine_n_iters": 12,
            },
        },
    )
    assert remove_resp.status_code == 200, remove_resp.text
    payload = remove_resp.json()
    assert payload["removed_object_id"] == object_id
    assert payload["history_size"] >= 2
    assert payload["objects"] == []
    assert payload["refine_requested"] is True
    assert payload["refine_enabled"] is True
    assert payload["refine_supported"] is True
    assert payload["refine_skip_reason"] == ""
    assert payload["refine_pipeline"] == "refine_predict"
    assert "refine=True" in payload["refine_overrides"]
    assert payload["mask_area_fraction"] == 0.12
    assert payload["refiner"]["n_iters"] == 12
    assert seen_inpaint_tuning.get("enable_refinement") is True
    assert seen_inpaint_tuning.get("refine_n_iters") == 12


def test_accuracy_presets_endpoint():
    response = client.get("/api/v3/accuracy-presets")
    assert response.status_code == 200
    payload = response.json()
    assert "segmentation" in payload
    assert "inpainting" in payload
    assert "refine_soft" in payload["inpainting"]
    assert "hq_refine" in payload["inpainting"]
    assert payload["inpainting"]["hq_refine"]["enable_refinement"] is True


def test_capstone_freehand_segmentation_registers_object(tmp_path, monkeypatch):
    capstone_scene_store.root = tmp_path / "scenes"
    capstone_scene_store.root.mkdir(parents=True, exist_ok=True)

    upload_bytes = io.BytesIO()
    Image.new("RGB", (256, 256), (245, 245, 245)).save(upload_bytes, format="PNG")
    upload_bytes.seek(0)

    upload_resp = client.post(
        "/api/v3/scenes/upload",
        files={"file": ("scene.png", upload_bytes.getvalue(), "image/png")},
        data={"title": "Freehand Scene"},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    scene_id = upload_resp.json()["scene"]["scene_id"]

    mask_path = _make_png(tmp_path / "freehand-mask.png", color=(255, 255, 255))

    def _fake_segment_freehand(image_url, paths, mode, brush_size_px, label, tuning=None, sam_refine=True):  # noqa: ARG001
        assert mode in {"brush", "lasso"}
        assert len(paths) == 1
        assert brush_size_px == 28
        return {
            "mask_url": str(mask_path),
            "bbox": [24, 30, 180, 220],
            "img_width": 256,
            "img_height": 256,
            "area_fraction": 0.2,
            "method": "sam2.1_freehand_refine",
            "score": 0.96,
            "tuning": tuning.model_dump() if tuning else {},
        }

    monkeypatch.setattr("app.routers.v3_capstone.sam2_segmenter.segment_from_freehand", _fake_segment_freehand)

    segment_resp = client.post(
        f"/api/v3/scenes/{scene_id}/segment-freehand",
        json={
            "paths": [
                {
                    "points": [
                        {"x": 0.20, "y": 0.25},
                        {"x": 0.45, "y": 0.48},
                        {"x": 0.65, "y": 0.62},
                    ]
                }
            ],
            "mode": "brush",
            "brush_size_px": 28,
            "label": "chair",
            "sam_refine": True,
        },
    )

    assert segment_resp.status_code == 200, segment_resp.text
    payload = segment_resp.json()
    assert payload["method"] == "sam2.1_freehand_refine"
    assert payload["scene_object_id"]

    scene_resp = client.get(f"/api/v3/scenes/{scene_id}")
    assert scene_resp.status_code == 200
    assert len(scene_resp.json()["objects"]) == 1
