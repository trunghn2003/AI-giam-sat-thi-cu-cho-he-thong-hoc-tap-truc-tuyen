"""
Face recognition module backed by InsightFace and a mean-embedding database.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import numpy as np

try:
    from insightface.app import FaceAnalysis
except ImportError as exc:  # pragma: no cover - runtime environment specific
    raise ImportError(
        "insightface is required for face recognition. "
        "Install it with `pip install insightface`."
    ) from exc

from .face_database import FaceDatabase
from .utils import bgr_to_rgb, ensure_uint8, serialize_bbox, to_float

LOGGER = logging.getLogger(__name__)


class FaceRecognizer:
    """
    Perform face detection, compute embeddings, and match against a database.
    """

    def __init__(
        self,
        dataset_dir: Path,
        providers: Optional[Sequence[str]] = None,
        ctx_id: int = -1,
        det_size: Iterable[int] = (640, 640),
        match_threshold: float = 0.5,
        database_filename: str = "face_database_kaggle.pkl",
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.providers = list(providers)
        self.ctx_id = ctx_id
        self.det_size = tuple(det_size)
        self.match_threshold = match_threshold
        self.database = FaceDatabase(self.dataset_dir.parent / "models" / database_filename)

        self._face_app = FaceAnalysis(providers=self.providers)
        self._face_app.prepare(ctx_id=self.ctx_id, det_size=self.det_size)

    def analyze(self, image_bgr: np.ndarray) -> List[dict]:
        """
        Run face detection + recognition on a BGR image.
        """
        image = ensure_uint8(image_bgr)
        rgb = bgr_to_rgb(image)
        faces = self._face_app.get(rgb)
        results = []
        for face in faces:
            embedding = getattr(face, "embedding", None)
            if embedding is None:
                LOGGER.debug("Face without embedding skipped")
                continue

            raw_label, similarity = self.database.identify(embedding)
            if self.match_threshold is not None and similarity < self.match_threshold:
                label = "Unknown"
            else:
                label = raw_label

            pose = getattr(face, "pose", (0.0, 0.0, 0.0))
            bbox = getattr(face, "bbox", None)
            result = {
                "label": str(label),
                "raw_label": str(raw_label),
                "confidence": similarity,
                "pose": [to_float(v) for v in pose] if pose is not None else None,
                "bbox": serialize_bbox(bbox) if bbox is not None else None,
            }
            results.append(result)
        return results

    def add_person(
        self,
        name: str,
        images_bgr: Iterable[np.ndarray],
        student_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> dict:
        """
        Add a new identity to the database using provided images.

        Args:
            name: Student's full name
            images_bgr: List of BGR images containing the student's face
            student_id: Student ID number
            email: Student's email address

        Returns:
            Dictionary describing ingestion statistics.
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Name must be provided")
        if self.database.has_person(clean_name):
            raise ValueError(f"Identity '{clean_name}' already exists in database")

        embeddings: List[np.ndarray] = []
        processed = 0
        face_hits = 0
        for raw_img in images_bgr:
            processed += 1
            image = ensure_uint8(raw_img)
            rgb = bgr_to_rgb(image)
            faces = self._face_app.get(rgb)
            if not faces:
                continue
            face_hits += 1
            embedding = getattr(faces[0], "embedding", None)
            if embedding is None:
                continue
            embeddings.append(np.asarray(embedding, dtype=np.float32))

        if not embeddings:
            raise ValueError("No valid faces detected in supplied images")

        count = self.database.add_person(
            clean_name, 
            embeddings,
            student_id=student_id,
            email=email
        )

        return {
            "name": clean_name,
            "processed_images": processed,
            "faces_detected": face_hits,
            "embeddings_used": count,
        }
