from __future__ import annotations

import io
import os
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.capstone.models import InpaintTuning, SegmentationTuning
from app.capstone.runtime import (
    get_capstone_runtime_settings,
    has_sam2,
    has_torch,
    resolve_device,
)
from app.rendering.storage import fetch_image_bytes, put_bytes, save_pil


class SAM2UnavailableError(RuntimeError):
    """Raised when SAM 2 cannot be used."""


class LaMaUnavailableError(RuntimeError):
    """Raised when LaMa cannot be used."""


def _load_image(image_url: str) -> Image.Image:
    return Image.open(io.BytesIO(fetch_image_bytes(image_url))).convert("RGB")


def _mask_bbox(mask_arr: np.ndarray) -> list[int]:
    ys, xs = np.where(mask_arr > 0)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _largest_component(mask_arr: np.ndarray) -> np.ndarray:
    h, w = mask_arr.shape
    visited = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []

    for y in range(h):
        for x in range(w):
            if visited[y, x] or mask_arr[y, x] == 0:
                continue
            stack = [(y, x)]
            component: list[tuple[int, int]] = []
            visited[y, x] = True
            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and mask_arr[ny, nx] > 0:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            if len(component) > len(best):
                best = component

    out = np.zeros_like(mask_arr, dtype=np.uint8)
    for y, x in best:
        out[y, x] = 255
    return out


def refine_mask(mask_arr: np.ndarray, tuning: Optional[SegmentationTuning | InpaintTuning]) -> np.ndarray:
    if tuning is None:
        return (mask_arr > 0).astype(np.uint8) * 255

    refined = (mask_arr > 0).astype(np.uint8) * 255
    if getattr(tuning, "keep_largest_component", False):
        refined = _largest_component(refined)

    image = Image.fromarray(refined, mode="L")
    erode_px = int(getattr(tuning, "erode_px", 0) or 0)
    dilate_px = int(
        getattr(tuning, "dilate_px", 0) or getattr(tuning, "mask_dilate_px", 0) or 0
    )

    for _ in range(erode_px):
        image = image.filter(ImageFilter.MinFilter(3))
    for _ in range(dilate_px):
        image = image.filter(ImageFilter.MaxFilter(3))
    return (np.array(image) > 0).astype(np.uint8) * 255


def _mock_ellipse(image_url: str, click_x: float, click_y: float, label: str) -> Dict:
    img = _load_image(image_url)
    w, h = img.size
    cx = int(click_x * w)
    cy = int(click_y * h)
    rx = max(int(w * 0.18), 24)
    ry = max(int(h * 0.18), 24)
    x0, y0 = max(0, cx - rx), max(0, cy - ry)
    x1, y1 = min(w, cx + rx), min(h, cy + ry)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([x0, y0, x1, y1], fill=255)
    mask_url = save_pil("capstone/masks", f"{label}-mock.png", mask, fmt="PNG")
    return {
        "mask_url": mask_url,
        "bbox": [x0, y0, x1, y1],
        "img_width": w,
        "img_height": h,
        "area_fraction": round(float(np.count_nonzero(np.array(mask)) / (w * h)), 4),
        "method": "mock_ellipse",
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _rasterize_freehand_mask(
    width: int,
    height: int,
    paths: Sequence[Sequence[Tuple[float, float]]],
    mode: str,
    brush_size_px: int,
) -> np.ndarray:
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    radius = max(1, int(brush_size_px // 2))

    for path in paths:
        points = [
            (
                int(round(_clamp01(x) * max(1, width - 1))),
                int(round(_clamp01(y) * max(1, height - 1))),
            )
            for x, y in path
        ]
        if len(points) < 2:
            continue

        if mode == "lasso" and len(points) >= 3:
            draw.polygon(points, fill=255, outline=255)
            continue

        draw.line(points, fill=255, width=max(1, brush_size_px), joint="curve")
        for cx, cy in points:
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)

    return (np.array(mask) > 0).astype(np.uint8) * 255


def _sample_positive_points(mask_arr: np.ndarray, max_points: int = 24) -> np.ndarray:
    ys, xs = np.where(mask_arr > 0)
    if len(xs) == 0:
        return np.empty((0, 2), dtype=np.float32)

    stride = max(1, int(len(xs) / max_points))
    idx = np.arange(0, len(xs), stride)[:max_points]
    coords = np.stack([xs[idx], ys[idx]], axis=1).astype(np.float32)
    return coords


def _mask_centroid_point(mask_arr: np.ndarray) -> np.ndarray:
    ys, xs = np.where(mask_arr > 0)
    if len(xs) == 0:
        return np.empty((0, 2), dtype=np.float32)
    centroid_x = float(np.mean(xs))
    centroid_y = float(np.mean(ys))
    return np.array([[centroid_x, centroid_y]], dtype=np.float32)


def _sample_negative_points(mask_arr: np.ndarray, max_points: int = 16) -> np.ndarray:
    h, w = mask_arr.shape
    bbox = _mask_bbox(mask_arr)
    x0, y0, x1, y1 = bbox
    pad = max(8, int(max(w, h) * 0.03))

    left = max(0, x0 - pad)
    right = min(w - 1, x1 + pad)
    top = max(0, y0 - pad)
    bottom = min(h - 1, y1 + pad)

    ring_points: List[Tuple[int, int]] = []
    # Perimeter sampling creates explicit negative hints around the sketch boundary.
    for x in np.linspace(left, right, num=10, dtype=int):
        ring_points.append((int(x), int(top)))
        ring_points.append((int(x), int(bottom)))
    for y in np.linspace(top, bottom, num=10, dtype=int):
        ring_points.append((int(left), int(y)))
        ring_points.append((int(right), int(y)))

    filtered = [(x, y) for x, y in ring_points if mask_arr[y, x] == 0]
    if not filtered:
        return np.empty((0, 2), dtype=np.float32)

    stride = max(1, int(len(filtered) / max_points))
    picked = filtered[::stride][:max_points]
    return np.array(picked, dtype=np.float32)


def _mask_prompt_box(mask_arr: np.ndarray, width: int, height: int) -> np.ndarray:
    x0, y0, x1, y1 = _mask_bbox(mask_arr)
    pad = max(4, int(max(width, height) * 0.015))
    return np.array(
        [
            max(0, x0 - pad),
            max(0, y0 - pad),
            min(width - 1, x1 + pad),
            min(height - 1, y1 + pad),
        ],
        dtype=np.float32,
    )


def _pick_best_snap_mask(
    masks: np.ndarray,
    sam_scores: np.ndarray,
    guide_mask: np.ndarray,
) -> int:
    guide = guide_mask > 0
    guide_area = float(np.count_nonzero(guide))
    best_idx = 0
    best_score = -1.0

    for idx, mask in enumerate(masks):
        pred = mask > 0
        pred_area = float(np.count_nonzero(pred))
        if pred_area == 0.0:
            continue

        intersection = float(np.count_nonzero(np.logical_and(pred, guide)))
        precision = intersection / pred_area
        recall = intersection / max(1.0, guide_area)
        dice = (2.0 * intersection) / max(1.0, pred_area + guide_area)
        model_score = float(sam_scores[idx])
        combined = (0.52 * dice) + (0.28 * precision) + (0.12 * recall) + (0.08 * model_score)

        if combined > best_score:
            best_score = combined
            best_idx = idx

    return int(best_idx)


def _is_sam2_torchvision_runtime_conflict(exc: Exception) -> bool:
    message = str(exc)
    if "InterpolationMode" in message and "___torch_mangle" in message:
        return True
    if "Can't redefine method: forward on class:" in message and "torchvision.transforms.transforms.Resize" in message:
        return True
    return False


def _is_sam2_image_state_error(exc: Exception) -> bool:
    message = str(exc)
    return "An image must be set with .set_image" in message and "before mask prediction" in message


_sam2_predictor_lock = RLock()


def _predict_with_set_image(predictor, image_arr: np.ndarray, **predict_kwargs):
    predictor.set_image(image_arr)
    try:
        return predictor.predict(**predict_kwargs)
    except Exception as exc:
        if not _is_sam2_image_state_error(exc):
            raise
        predictor.set_image(image_arr)
        return predictor.predict(**predict_kwargs)


class SAM2ClickSegmenter:
    def __init__(self) -> None:
        self.settings = get_capstone_runtime_settings()
        self.device = resolve_device(self.settings.device_preference)

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

    def segment_from_click(
        self,
        image_url: str,
        click_x: float,
        click_y: float,
        label: str = "object",
        tuning: Optional[SegmentationTuning] = None,
    ) -> Dict:
        state = self.status()
        if not bool(state["ready"]):
            if self.settings.allow_mock_fallbacks:
                return _mock_ellipse(image_url, click_x, click_y, label)
            raise SAM2UnavailableError(
                "SAM 2 is not ready. Set CAPSTONE_SAM2_CHECKPOINT and install the sam2 package."
            )

        predictor = _sam2_predictor(
            self.settings.sam2_config,
            str(self.settings.resolved_sam2_checkpoint),
            self.device,
        )
        img = _load_image(image_url)
        arr = np.array(img)
        h, w = arr.shape[:2]
        point_coords = np.array([[click_x * w, click_y * h]], dtype=np.float32)
        point_labels = np.array([1], dtype=np.int32)
        with _sam2_predictor_lock:
            masks, scores, _ = _predict_with_set_image(
                predictor,
                arr,
                point_coords=point_coords,
                point_labels=point_labels,
                multimask_output=True,
            )
        if tuning and tuning.multimask_strategy == "largest_mask":
            areas = [float(mask.sum()) for mask in masks]
            best_idx = int(np.argmax(areas))
        else:
            best_idx = int(np.argmax(scores))

        best = (masks[best_idx] > 0).astype(np.uint8) * 255
        refined = refine_mask(best, tuning)
        area_fraction = float(np.count_nonzero(refined) / (w * h))
        min_area = tuning.min_area_fraction if tuning else 0.0
        if area_fraction < min_area:
            raise RuntimeError(
                f"Segmented mask too small ({area_fraction:.5f} < {min_area:.5f}); adjust click or tuning."
            )

        mask_img = Image.fromarray(refined, mode="L")
        bbox = _mask_bbox(refined)
        mask_url = save_pil("capstone/masks", f"{label}-sam2.png", mask_img, fmt="PNG")
        return {
            "mask_url": mask_url,
            "bbox": bbox,
            "img_width": w,
            "img_height": h,
            "area_fraction": round(area_fraction, 4),
            "method": "sam2.1_click",
            "score": float(scores[best_idx]),
            "tuning": tuning.model_dump() if tuning else {},
        }

    def segment_from_freehand(
        self,
        image_url: str,
        paths: Sequence[Sequence[Tuple[float, float]]],
        mode: str = "brush",
        brush_size_px: int = 24,
        label: str = "object",
        tuning: Optional[SegmentationTuning] = None,
        sam_refine: bool = True,
    ) -> Dict:
        img = _load_image(image_url)
        arr = np.array(img)
        h, w = arr.shape[:2]

        drawn_mask = _rasterize_freehand_mask(w, h, paths, mode=mode, brush_size_px=brush_size_px)
        if int(np.count_nonzero(drawn_mask)) == 0:
            raise RuntimeError("Freehand mask is empty; draw at least one visible stroke")

        working_mask = drawn_mask
        method = "freehand_drawn_mask"
        score: Optional[float] = None

        state = self.status()
        if sam_refine and bool(state["ready"]):
            predictor = _sam2_predictor(
                self.settings.sam2_config,
                str(self.settings.resolved_sam2_checkpoint),
                self.device,
            )

            if mode == "lasso":
                point_coords = _mask_centroid_point(drawn_mask)
            else:
                point_coords = _sample_positive_points(drawn_mask, max_points=24)
            if len(point_coords) > 0:
                negative_coords = _sample_negative_points(drawn_mask, max_points=16)
                if len(negative_coords) > 0:
                    point_coords = np.concatenate([point_coords, negative_coords], axis=0)
                    positive_labels = np.ones((point_coords.shape[0] - negative_coords.shape[0],), dtype=np.int32)
                    negative_labels = np.zeros((negative_coords.shape[0],), dtype=np.int32)
                    point_labels = np.concatenate([positive_labels, negative_labels], axis=0)
                else:
                    point_labels = np.ones((point_coords.shape[0],), dtype=np.int32)

                box = _mask_prompt_box(drawn_mask, w, h)
                used_retry_fallback = False
                with _sam2_predictor_lock:
                    try:
                        masks, scores, _ = _predict_with_set_image(
                            predictor,
                            arr,
                            point_coords=point_coords,
                            point_labels=point_labels,
                            box=box,
                            multimask_output=True,
                        )
                    except Exception as exc:
                        if not (_is_sam2_torchvision_runtime_conflict(exc) or _is_sam2_image_state_error(exc)):
                            raise

                        try:
                            if mode == "lasso":
                                retry_coords = _mask_centroid_point(drawn_mask)
                            else:
                                retry_coords = _sample_positive_points(drawn_mask, max_points=8)
                            retry_labels = np.ones((retry_coords.shape[0],), dtype=np.int32)
                            masks, scores, _ = _predict_with_set_image(
                                predictor,
                                arr,
                                point_coords=retry_coords,
                                point_labels=retry_labels,
                                multimask_output=True,
                            )
                            used_retry_fallback = True
                        except Exception as retry_exc:
                            if not (_is_sam2_torchvision_runtime_conflict(retry_exc) or _is_sam2_image_state_error(retry_exc)):
                                raise
                            method = "freehand_drawn_mask_sam_fallback"
                            masks = None
                            scores = None

                if masks is not None and scores is not None:
                    best_idx = _pick_best_snap_mask(masks, scores, drawn_mask)
                    sam_mask = (masks[best_idx] > 0).astype(np.uint8) * 255
                    outside = float(np.count_nonzero((sam_mask > 0) & (drawn_mask == 0)))
                    area = float(np.count_nonzero(sam_mask))
                    if area > 0 and (outside / area) > 0.6:
                        working_mask = np.where((sam_mask > 0) & (drawn_mask > 0), 255, 0).astype(np.uint8)
                    else:
                        working_mask = sam_mask

                    if used_retry_fallback:
                        method = "sam2.1_auto_snap_retry" if mode == "lasso" else "sam2.1_auto_snap_brush_retry"
                    else:
                        method = "sam2.1_auto_snap_lasso" if mode == "lasso" else "sam2.1_auto_snap_brush"
                    score = float(scores[best_idx])
                else:
                    method = "freehand_drawn_mask_sam_fallback"

        refined = refine_mask(working_mask, tuning)
        area_fraction = float(np.count_nonzero(refined) / (w * h))
        min_area = tuning.min_area_fraction if tuning else 0.0
        if area_fraction < min_area:
            raise RuntimeError(
                f"Segmented mask too small ({area_fraction:.5f} < {min_area:.5f}); adjust freehand selection or tuning."
            )
        if int(np.count_nonzero(refined)) == 0:
            raise RuntimeError("Refined freehand mask is empty after morphology; reduce erode settings")

        mask_img = Image.fromarray(refined, mode="L")
        bbox = _mask_bbox(refined)
        mask_url = save_pil("capstone/masks", f"{label}-freehand.png", mask_img, fmt="PNG")
        payload = {
            "mask_url": mask_url,
            "bbox": bbox,
            "img_width": w,
            "img_height": h,
            "area_fraction": round(area_fraction, 4),
            "method": method,
            "tuning": tuning.model_dump() if tuning else {},
        }
        if score is not None:
            payload["score"] = score
        return payload


@lru_cache(maxsize=1)
def _sam2_predictor(config_path: str, checkpoint_path: str, device: str):
    from sam2.build_sam import build_sam2  # noqa: WPS433
    from sam2.sam2_image_predictor import SAM2ImagePredictor  # noqa: WPS433

    model = build_sam2(config_path, checkpoint_path, device=device)
    return SAM2ImagePredictor(model)


@lru_cache(maxsize=1)
def _lama_predict_supports_refine(script_path: str) -> bool:
    try:
        text = Path(script_path).read_text(encoding="utf-8")
    except Exception:
        return False
    return "refine_predict" in text and "predict_config.get('refine'" in text


class LaMaInpainter:
    def __init__(self) -> None:
        self.settings = get_capstone_runtime_settings()

    def status(self) -> Dict[str, object]:
        repo = self.settings.resolved_lama_repo_path
        model = self.settings.resolved_lama_model_path
        script = (repo / "bin" / "predict.py") if repo else None
        refine_supported = bool(script and script.exists() and _lama_predict_supports_refine(str(script)))
        return {
            "repo_path": str(repo) if repo else None,
            "repo_exists": bool(repo and repo.exists()),
            "predict_script": str(script) if script else None,
            "predict_script_exists": bool(script and script.exists()),
            "model_path": str(model) if model else None,
            "model_exists": bool(model and model.exists()),
            "refine_supported": refine_supported,
            "refiner_defaults": {
                "gpu_ids": self.settings.lama_refiner_gpu_ids,
                "modulo": self.settings.lama_refiner_modulo,
                "n_iters": self.settings.lama_refiner_n_iters,
                "lr": self.settings.lama_refiner_lr,
                "min_side": self.settings.lama_refiner_min_side,
                "max_scales": self.settings.lama_refiner_max_scales,
                "px_budget": self.settings.lama_refiner_px_budget,
                "max_mask_area_fraction": self.settings.lama_refiner_max_mask_area_fraction,
            },
            "python_executable": self.settings.lama_python_executable,
            "device": resolve_device(self.settings.device_preference),
            "ready": bool(repo and repo.exists() and script and script.exists() and model and model.exists()),
        }

    def inpaint(self, image_url: str, mask_url: str, tuning: Optional[InpaintTuning] = None) -> Dict:
        state = self.status()
        if not bool(state["ready"]):
            raise LaMaUnavailableError(
                "LaMa is not ready. Set CAPSTONE_LAMA_REPO_PATH and CAPSTONE_LAMA_MODEL_PATH."
            )

        image = _load_image(image_url)
        mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.NEAREST)
        mask_arr = np.array(mask.point(lambda px: 255 if px >= 127 else 0))
        mask = Image.fromarray(refine_mask(mask_arr, tuning), mode="L")
        mask_np = np.array(mask)
        mask_area_fraction = float(np.count_nonzero(mask_np) / max(1, mask_np.size))

        repo = self.settings.resolved_lama_repo_path
        model = self.settings.resolved_lama_model_path
        assert repo is not None
        assert model is not None
        device = resolve_device(self.settings.device_preference)
        script_path = repo / "bin" / "predict.py"
        refine_supported = _lama_predict_supports_refine(str(script_path))
        refine_requested = bool(tuning and tuning.enable_refinement)
        use_refine = refine_requested
        refine_skip_reason = ""

        if use_refine and mask_area_fraction > self.settings.lama_refiner_max_mask_area_fraction:
            use_refine = False
            refine_skip_reason = (
                "Skipped refinement because the mask covers too much area "
                f"({mask_area_fraction:.3f} > {self.settings.lama_refiner_max_mask_area_fraction:.3f})."
            )

        if use_refine and not refine_supported:
            raise LaMaUnavailableError(
                "Current LaMa predict.py does not support refine=True overrides. "
                "Point CAPSTONE_LAMA_REPO_PATH to a refinement-enabled LaMa repo."
            )
        if use_refine and device != "cuda":
            raise LaMaUnavailableError("Big-LaMa refinement requires CUDA; set CAPSTONE_DEVICE=cuda")

        refine_gpu_ids = (
            tuning.refine_gpu_ids if (tuning and tuning.refine_gpu_ids) else self.settings.lama_refiner_gpu_ids
        )
        refine_gpu_ids = (refine_gpu_ids or "0,").replace("'", "").replace('"', "").strip()
        if not refine_gpu_ids:
            refine_gpu_ids = "0,"
        refine_modulo = (
            tuning.refine_modulo if (tuning and tuning.refine_modulo is not None) else self.settings.lama_refiner_modulo
        )
        refine_n_iters = tuning.refine_n_iters if tuning else self.settings.lama_refiner_n_iters
        refine_lr = tuning.refine_lr if tuning else self.settings.lama_refiner_lr
        refine_min_side = tuning.refine_min_side if tuning else self.settings.lama_refiner_min_side
        refine_max_scales = tuning.refine_max_scales if tuning else self.settings.lama_refiner_max_scales
        refine_px_budget = tuning.refine_px_budget if tuning else self.settings.lama_refiner_px_budget

        runtime_root = Path(__file__).resolve().parents[2] / "uploads" / "capstone-runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="capstone-lama-", dir=str(runtime_root)) as tmpdir:
            base = Path(tmpdir)
            indir = base / "input"
            outdir = base / "output"
            indir.mkdir(parents=True, exist_ok=True)
            outdir.mkdir(parents=True, exist_ok=True)

            image_path = indir / "sample.png"
            mask_path = indir / "sample_mask.png"
            image.save(image_path, format="PNG")
            mask.save(mask_path, format="PNG")

            rel_model = Path(os.path.relpath(model, start=base)).as_posix()
            command = [
                self.settings.lama_python_executable,
                str(script_path),
                f"model.path={rel_model}",
                "indir=input",
                "outdir=output",
                "dataset.img_suffix=.png",
                f"device={device}",
                "hydra.run.dir=.",
                "hydra.output_subdir=null",
            ]
            if use_refine:
                command.extend(
                    [
                        "refine=True",
                        f"refiner.gpu_ids='{refine_gpu_ids}'",
                        f"refiner.modulo={refine_modulo}",
                        f"refiner.n_iters={refine_n_iters}",
                        f"refiner.lr={refine_lr}",
                        f"refiner.min_side={refine_min_side}",
                        f"refiner.max_scales={refine_max_scales}",
                        f"refiner.px_budget={refine_px_budget}",
                    ]
                )
            refine_overrides = [
                arg for arg in command if arg.startswith("refine=") or arg.startswith("refiner.")
            ]
            env = dict(os.environ)
            env["PYTHONPATH"] = str(repo) + (
                os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
            )
            completed = subprocess.run(
                command,
                cwd=str(base),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    "LaMa predict failed: "
                    + "\n".join(
                        line for line in [completed.stdout[-1000:], completed.stderr[-1000:]] if line
                    )
                )

            result_path = outdir / "sample.png"
            if not result_path.exists():
                candidates = sorted(outdir.glob("*.png"))
                if not candidates:
                    raise RuntimeError("LaMa predict completed but no output image was produced")
                result_path = candidates[0]

            result_bytes = result_path.read_bytes()
            result_url = put_bytes("capstone/inpaints", "lama-result.png", result_bytes, mime="image/png")
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
                "refiner": {
                    "gpu_ids": refine_gpu_ids,
                    "modulo": refine_modulo,
                    "n_iters": refine_n_iters,
                    "lr": refine_lr,
                    "min_side": refine_min_side,
                    "max_scales": refine_max_scales,
                    "px_budget": refine_px_budget,
                }
                if use_refine
                else {},
                "stdout_tail": completed.stdout[-500:],
                "tuning": tuning.model_dump() if tuning else {},
            }


sam2_segmenter = SAM2ClickSegmenter()
lama_inpainter = LaMaInpainter()
