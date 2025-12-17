"""
High-level orchestration for the cheating detection system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    DEFAULT_FACE_DATASET_DIR,
    DEFAULT_HEAD_POSE_THRESHOLDS,
    DEFAULT_YOLO_MODEL_PATH,
    resolve_path,
)
from .face_recognition import FaceRecognizer
from .gaze import EyeGazeEstimator
from .head_pose import HeadPoseClassifier, HeadPoseThresholds
from .object_detection import SuspiciousObjectDetector
from .utils import ensure_uint8
from .visualization import annotate_detections
import numpy as np


@dataclass
class DetectionOptions:
    """
    Configuration for the cheating detection pipeline.
    """

    face_dataset_dir: Path = field(
        default_factory=lambda: resolve_path(DEFAULT_FACE_DATASET_DIR)
    )
    yolo_model_path: Path = field(
        default_factory=lambda: resolve_path(DEFAULT_YOLO_MODEL_PATH)
    )
    head_pose_thresholds: HeadPoseThresholds = field(
        default_factory=lambda: HeadPoseThresholds(**DEFAULT_HEAD_POSE_THRESHOLDS)
    )
    watched_objects: Optional[List[str]] = None
    face_similarity_threshold: Optional[float] = 0.5


class CheatingDetectionPipeline:
    """
    Aggregate face recognition, head pose analysis, and object detection.
    """

    def __init__(self, options: DetectionOptions | None = None) -> None:
        self.options = options or DetectionOptions()

        self.face_recognizer = FaceRecognizer(
            self.options.face_dataset_dir,
            match_threshold=(
                self.options.face_similarity_threshold
                if self.options.face_similarity_threshold is not None
                else 0.0
            ),
        )
        self.object_detector = SuspiciousObjectDetector(
            self.options.yolo_model_path, watched_classes=self.options.watched_objects
        )
        self.head_pose = HeadPoseClassifier(self.options.head_pose_thresholds)
        self.eye_gaze = EyeGazeEstimator()

    def analyze(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        image = ensure_uint8(image_bgr)

        faces = self.face_recognizer.analyze(image)
        objects = self.object_detector.analyze(image)

        flags: List[str] = []
        enriched_faces: List[Dict[str, Any]] = []

        face_count = len(faces)
        if face_count == 0:
            flags.append("No face detected")
        elif face_count > 1:
            flags.append(f"Multiple faces detected ({face_count})")

        bbox_indices = [
            (idx, face["bbox"])
            for idx, face in enumerate(faces)
            if face.get("bbox")
        ]
        gaze_map = {}
        if bbox_indices:
            _, bbox_list = zip(*bbox_indices)
            gaze_estimates = self.eye_gaze.estimate(image, bbox_list)
            for local_idx, estimate in gaze_estimates.items():
                face_idx = bbox_indices[local_idx][0]
                gaze_map[face_idx] = estimate

        for idx, face in enumerate(faces):
            pose = face.get("pose")
            orientation = None
            if pose:
                orientation = self.head_pose.classify_sequence(pose)
                face["orientation"] = orientation
                if orientation != "Straight":
                    flags.append(
                        f"Head orientation '{orientation}' detected for {face['label']}"
                    )
            if idx in gaze_map:
                gaze = gaze_map[idx]
                face["gaze"] = gaze.direction
                face["gaze_metrics"] = {
                    "horizontal_ratio": gaze.horizontal_ratio,
                    "vertical_ratio": gaze.vertical_ratio,
                }
                if gaze.direction != "Center":
                    flags.append(
                        f"Gaze {gaze.direction} detected for {face['label']}"
                    )

            confidence = face.get("confidence")
            raw_label = face.get("raw_label")
            if (
                self.options.face_similarity_threshold is not None
                and confidence is not None
                and confidence < self.options.face_similarity_threshold
            ):
                flags.append(
                    "Low face similarity "
                    f"({confidence:.2f}) for {raw_label or face['label']}"
                )
            enriched_faces.append(face)

        if objects:
            flags.append("Suspicious object(s) detected")

        status = "clear" if not flags else "attention"

        # Prepare result dict for annotation
        result_dict = {
            "status": status,
            "faces": enriched_faces,
            "objects": objects,
            "flags": flags,
            "face_count": face_count,
        }

        # Create annotated image with all detections drawn
        annotated_image = annotate_detections(image.copy(), result_dict)
        result_dict["annotated_image"] = annotated_image

        return result_dict


def load_default_pipeline() -> CheatingDetectionPipeline:
    """
    Convenience helper to build a pipeline with repository defaults.
    """

    return CheatingDetectionPipeline()
