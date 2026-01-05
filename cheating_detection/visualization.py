"""
Utilities for drawing detection results onto images.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

import cv2
import numpy as np


def annotate_detections(
    image_bgr: np.ndarray,
    detection_result: Dict[str, Any],
    face_color: Tuple[int, int, int] = (0, 200, 0),
    object_color: Tuple[int, int, int] = (0, 128, 255),
) -> np.ndarray:
    """
    Draw detected faces and objects along with labels on the image.
    """
    annotated = image_bgr.copy()

    for face in detection_result.get("faces", []):
        bbox = face.get("bbox")
        if bbox:
            _draw_bbox_with_label(
                annotated,
                bbox,
                _format_face_label(face),
                color=face_color,
            )

    for obj in detection_result.get("objects", []):
        bbox = obj.get("bbox")
        if bbox:
            _draw_bbox_with_label(
                annotated,
                bbox,
                _format_object_label(obj),
                color=object_color,
            )

    return annotated


def _draw_bbox_with_label(
    image: np.ndarray,
    bbox: Iterable[float],
    label: str,
    color: Tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    _draw_label(image, label, (x1, y1 - 10), color)


def _draw_label(
    image: np.ndarray,
    text: str,
    origin: Tuple[int, int],
    color: Tuple[int, int, int],
    font_scale: float = 0.5,
    thickness: int = 1,
) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, baseline = cv2.getTextSize(text, font, font_scale, thickness)
    text_w, text_h = text_size
    
    img_h, img_w = image.shape[:2]
    x, y = origin

    # Adjust x to keep text within image width
    if x + text_w > img_w:
        x = img_w - text_w
    x = max(0, x)

    # Adjust y to keep text within image height
    # If the text block goes above the image (y - text_h - baseline < 0)
    # Move it down (e.g., inside the bounding box)
    if y - text_h - baseline < 0:
        y = text_h + baseline + 5
    
    # Check if it goes off bottom (unlikely for top labels but good practice)
    if y + baseline > img_h:
        y = img_h - baseline

    cv2.rectangle(
        image,
        (x, y - text_h - baseline),
        (x + text_size[0], y + baseline),
        color,
        cv2.FILLED,
    )
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )


def _format_face_label(face: Dict[str, Any]) -> str:
    label = face.get("label") or "Unknown"
    confidence = face.get("confidence")
    orientation = face.get("orientation")
    gaze = face.get("gaze")
    parts = [label]
    if confidence is not None:
        parts.append(f"{confidence:.2f}")
    if orientation and orientation != "Straight":
        parts.append(orientation)
    if gaze and gaze != "Center":
        parts.append(gaze)
    return " | ".join(parts)


def _format_object_label(obj: Dict[str, Any]) -> str:
    label = obj.get("label") or "object"
    confidence = obj.get("confidence")
    if confidence is None:
        return label
    return f"{label} {confidence:.2f}"
