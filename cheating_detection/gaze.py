"""
Eye gaze estimation using MediaPipe Face Mesh iris landmarks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError as exc:  # pragma: no cover - environment dependent
    raise ImportError(
        "mediapipe is required for eye gaze estimation. "
        "Install it with `pip install mediapipe`."
    ) from exc

LOGGER = logging.getLogger(__name__)


LEFT_IRIS = (468, 469, 470, 471)
RIGHT_IRIS = (473, 474, 475, 476)
LEFT_EYE_CORNERS = (33, 133)
RIGHT_EYE_CORNERS = (362, 263)
LEFT_EYE_LIDS = (159, 145)
RIGHT_EYE_LIDS = (386, 374)


@dataclass
class GazeEstimate:
    direction: str
    horizontal_ratio: float
    vertical_ratio: float


class EyeGazeEstimator:
    """
    Estimate coarse gaze direction for detected faces.
    """

    def __init__(
        self,
        max_faces: int = 5,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=max_faces,
            refine_landmarks=True,  # Required to obtain iris points
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def estimate(
        self,
        image_bgr: np.ndarray,
        bboxes: Sequence[Sequence[float]],
    ) -> Dict[int, GazeEstimate]:
        """
        Estimate gaze for each face bounding box.

        Returns a mapping from index in `bboxes` to GazeEstimate.
        """
        if not bboxes:
            return {}
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        height, width = image_bgr.shape[:2]
        mesh_landmarks = results.multi_face_landmarks or []

        if not mesh_landmarks:
            return {}

        mesh_centers = [
            _compute_mesh_center(landmarks, width, height)
            for landmarks in mesh_landmarks
        ]
        bbox_centers = [
            ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0) for bbox in bboxes
        ]

        assignments = _assign_mesh_to_bboxes(mesh_centers, bbox_centers)

        estimates: Dict[int, GazeEstimate] = {}
        for bbox_idx, mesh_idx in assignments.items():
            landmarks = mesh_landmarks[mesh_idx]
            coords = np.array(
                [
                    [landmark.x * width, landmark.y * height]
                    for landmark in landmarks.landmark
                ],
                dtype=np.float32,
            )
            try:
                estimate = _classify_gaze(coords)
            except ValueError as exc:
                LOGGER.debug("Gaze classification skipped: %s", exc)
                continue
            estimates[bbox_idx] = estimate
        return estimates

    def close(self) -> None:
        self.face_mesh.close()


def _compute_mesh_center(
    landmarks: "mp.framework.formats.landmark_pb2.NormalizedLandmarkList",
    width: int,
    height: int,
) -> Tuple[float, float]:
    xs = [landmark.x * width for landmark in landmarks.landmark]
    ys = [landmark.y * height for landmark in landmarks.landmark]
    return float(np.mean(xs)), float(np.mean(ys))


def _assign_mesh_to_bboxes(
    mesh_centers: Sequence[Tuple[float, float]],
    bbox_centers: Sequence[Tuple[float, float]],
) -> Dict[int, int]:
    assignments: Dict[int, int] = {}
    if not mesh_centers or not bbox_centers:
        return assignments
    mesh_taken: set[int] = set()
    for bbox_idx, bbox_center in enumerate(bbox_centers):
        distances = [
            (mesh_idx, np.linalg.norm(np.asarray(bbox_center) - np.asarray(mesh_center)))
            for mesh_idx, mesh_center in enumerate(mesh_centers)
            if mesh_idx not in mesh_taken
        ]
        if not distances:
            continue
        mesh_idx = min(distances, key=lambda x: x[1])[0]
        assignments[bbox_idx] = mesh_idx
        mesh_taken.add(mesh_idx)
    return assignments


def _classify_gaze(coords: np.ndarray) -> GazeEstimate:
    """
    Classify gaze direction from landmark coordinates.
    """
    try:
        left_ratio_h = _horizontal_ratio(coords, LEFT_EYE_CORNERS, LEFT_IRIS)
        right_ratio_h = _horizontal_ratio(coords, RIGHT_EYE_CORNERS, RIGHT_IRIS)
        horizontal_ratio = float(np.mean([left_ratio_h, right_ratio_h]))

        left_ratio_v = _vertical_ratio(coords, LEFT_EYE_LIDS, LEFT_IRIS)
        right_ratio_v = _vertical_ratio(coords, RIGHT_EYE_LIDS, RIGHT_IRIS)
        vertical_ratio = float(np.mean([left_ratio_v, right_ratio_v]))
    except Exception as exc:
        raise ValueError(f"Failed to compute gaze ratios: {exc}") from exc

    # Calculate Eye Openness (Height-to-Width Ratio)
    try:
        # Left Eye Dimensions
        l_width = np.linalg.norm(coords[LEFT_EYE_CORNERS[1]] - coords[LEFT_EYE_CORNERS[0]])
        l_height = np.linalg.norm(coords[LEFT_EYE_LIDS[1]] - coords[LEFT_EYE_LIDS[0]])
        
        # Right Eye Dimensions
        r_width = np.linalg.norm(coords[RIGHT_EYE_CORNERS[1]] - coords[RIGHT_EYE_CORNERS[0]])
        r_height = np.linalg.norm(coords[RIGHT_EYE_LIDS[1]] - coords[RIGHT_EYE_LIDS[0]])
        
        # Avoid division by zero
        l_ratio = l_height / l_width if l_width > 1e-6 else 0
        r_ratio = r_height / r_width if r_width > 1e-6 else 0
        
        avg_openness = (l_ratio + r_ratio) / 2.0
        
        # If eyes are too closed (squinting, blinking, or looking down heavily), skip vertical gaze check
        # This prevents false "Looking Up" when eyes are barely visible
        eye_too_closed = avg_openness < 0.18

    except Exception:
        eye_too_closed = False

    direction = "Center"
    if horizontal_ratio < 0.35:
        direction = "Looking Left"
    elif horizontal_ratio > 0.65:
        direction = "Looking Right"
    elif not eye_too_closed:
        if vertical_ratio < 0.15:
            direction = "Looking Down"
        elif vertical_ratio > 0.65:
            direction = "Looking Up"

    return GazeEstimate(direction, horizontal_ratio, vertical_ratio)


def _horizontal_ratio(
    coords: np.ndarray,
    eye_corners: Tuple[int, int],
    iris_indices: Tuple[int, int, int, int],
) -> float:
    left_corner = coords[eye_corners[0]]
    right_corner = coords[eye_corners[1]]
    iris_center = coords[list(iris_indices)].mean(axis=0)
    denominator = right_corner[0] - left_corner[0]
    if abs(denominator) < 1e-6:
        raise ValueError("Invalid eye corner geometry")
    ratio = (iris_center[0] - left_corner[0]) / denominator
    return float(np.clip(ratio, 0.0, 1.0))


def _vertical_ratio(
    coords: np.ndarray,
    eyelids: Tuple[int, int],
    iris_indices: Tuple[int, int, int, int],
) -> float:
    top_lid = coords[eyelids[0]]
    bottom_lid = coords[eyelids[1]]
    iris_center = coords[list(iris_indices)].mean(axis=0)
    denominator = bottom_lid[1] - top_lid[1]
    if abs(denominator) < 1e-6:
        raise ValueError("Invalid eyelid geometry")
    ratio = (iris_center[1] - top_lid[1]) / denominator
    return float(np.clip(ratio, 0.0, 1.0))
