"""
Persistent storage for face embeddings using simple mean encoding.
"""

from __future__ import annotations

import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

LOGGER = logging.getLogger(__name__)


class FaceDatabase:
    """
    Manage a dictionary mapping person labels to mean face embeddings.
    Also stores metadata for each student (student_id, email, registration_date).
    """

    def __init__(self, database_path: Path) -> None:
        self.path = Path(database_path)
        self._embeddings: Dict[str, np.ndarray] = {}
        self._metadata: Dict[str, Dict[str, str]] = {}  # Store student metadata
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            LOGGER.warning("Face database not found at %s. Starting empty.", self.path)
            self._embeddings = {}
            self._metadata = {}
            return
        with self.path.open("rb") as handle:
            raw = pickle.load(handle)
        
        # Support both old format (dict of embeddings) and new format (dict with embeddings and metadata)
        if isinstance(raw, dict) and "embeddings" in raw:
            # New format
            self._embeddings = {
                str(name): np.asarray(embedding, dtype=np.float32)
                for name, embedding in raw["embeddings"].items()
            }
            self._metadata = raw.get("metadata", {})
        else:
            # Old format - just embeddings
            self._embeddings = {
                str(name): np.asarray(embedding, dtype=np.float32)
                for name, embedding in raw.items()
            }
            self._metadata = {}
        LOGGER.info("Loaded face database with %d identities", len(self._embeddings))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "embeddings": self._embeddings,
            "metadata": self._metadata
        }
        with self.path.open("wb") as handle:
            pickle.dump(data, handle)
        LOGGER.info("Persisted face database with %d identities", len(self._embeddings))

    @property
    def people(self) -> Tuple[str, ...]:
        return tuple(sorted(self._embeddings.keys()))

    def has_person(self, name: str) -> bool:
        return name in self._embeddings

    def add_person(
        self, 
        name: str, 
        embeddings: Iterable[np.ndarray],
        student_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> int:
        """
        Add a new person using the mean embedding of the provided vectors.

        Args:
            name: Student's full name
            embeddings: Face embeddings from multiple images
            student_id: Student ID number
            email: Student's email address

        Returns:
            Number of embeddings that were consumed.
        """
        vectors = [
            np.asarray(embedding, dtype=np.float32)
            for embedding in embeddings
            if embedding is not None
        ]
        if not vectors:
            raise ValueError("No embeddings supplied for new identity")
        mean_embedding = np.mean(vectors, axis=0)
        self._embeddings[name] = mean_embedding
        
        # Store metadata
        self._metadata[name] = {
            "student_id": student_id or "",
            "email": email or "",
            "registration_date": datetime.now().isoformat(),
        }
        
        self.save()
        return len(vectors)

    def identify(self, embedding: np.ndarray) -> Tuple[str, float]:
        """
        Identify the closest person based on cosine similarity.

        Returns:
            A tuple of (name, score). Score is in [-1, 1]; higher is better.
            If the database is empty, returns ("Unknown", 0.0).
        """
        if not self._embeddings:
            return "Unknown", 0.0
        query = _normalize(embedding)
        best_score = -1.0
        best_name = "Unknown"
        for name, stored in self._embeddings.items():
            score = float(np.dot(query, _normalize(stored)))
            if score > best_score:
                best_score = score
                best_name = name
        return best_name, best_score

    def get_student_info(self, name: str) -> Optional[Dict[str, str]]:
        """
        Get metadata for a specific student.
        
        Args:
            name: Student's name
            
        Returns:
            Dictionary with student_id, email, registration_date or None if not found
        """
        return self._metadata.get(name)

    def get_all_students(self) -> List[Dict[str, str]]:
        """
        Get list of all registered students with their metadata.
        
        Returns:
            List of dictionaries containing name and metadata for each student
        """
        students = []
        for name in sorted(self._embeddings.keys()):
            student_info = {
                "name": name,
                **self._metadata.get(name, {})
            }
            students.append(student_info)
        return students

    def delete_person(self, name: str) -> bool:
        """
        Remove a person from the database.
        
        Args:
            name: Person's name to remove
            
        Returns:
            True if person was removed, False if person didn't exist
        """
        if name not in self._embeddings:
            return False
        del self._embeddings[name]
        if name in self._metadata:
            del self._metadata[name]
        self.save()
        return True

    def find_by_student_id(self, student_id: str) -> Optional[str]:
        """
        Find student name by student ID.
        
        Args:
            student_id: Student ID to search for
            
        Returns:
            Student name if found, None otherwise
        """
        for name, metadata in self._metadata.items():
            if metadata.get("student_id") == student_id:
                return name
        return None


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm
