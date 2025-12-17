"""
Object detection module built on top of Ultralytics YOLO models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

import numpy as np

try:
    from ultralytics import YOLO
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ultralytics is required for object detection. "
        "Install it with `pip install ultralytics`."
    ) from exc

from .utils import ensure_uint8, serialize_bbox, to_float


class SuspiciousObjectDetector:
    """
    Wrap a YOLO model to surface objects of interest.
    """

    def __init__(
        self,
        model_path: Path,
        watched_classes: Optional[Sequence[str]] = None,
        confidence_threshold: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {self.model_path}")
        self.model = YOLO(str(self.model_path))
        self.watched_classes: Optional[Set[str]] = (
            set(watched_classes) if watched_classes else None
        )
        self.confidence_threshold = confidence_threshold

    def analyze(self, image_bgr: np.ndarray) -> List[dict]:
        image = ensure_uint8(image_bgr)
        results = self.model.predict(
            image, verbose=False, conf=self.confidence_threshold
        )
        detections: List[dict] = []
        if not results:
            return detections
        result = results[0]
        names = result.names or self.model.names
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections

        for box in boxes:
            cls_idx = int(box.cls[0])
            label = names.get(cls_idx, str(cls_idx)) if isinstance(names, dict) else str(
                names[cls_idx] if cls_idx < len(names) else cls_idx
            )
            if self.watched_classes and label not in self.watched_classes:
                continue
            confidence = to_float(box.conf[0])
            bbox = serialize_bbox(box.xyxy[0].tolist())
            detections.append(
                {
                    "label": label,
                    "confidence": confidence,
                    "bbox": bbox,
                }
            )
        return detections
