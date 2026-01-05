"""
Head pose analysis helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence, Tuple


@dataclass
class HeadPoseThresholds:
    yaw: float = 20.0
    pitch: float = 20.0
    roll: float = 20.0


class HeadPoseClassifier:
    """
    Classify coarse head orientation using Euler angles (degrees).
    """

    def __init__(
        self,
        thresholds: HeadPoseThresholds | Mapping[str, float] | None = None,
        pose_order: Sequence[str] = ("pitch", "yaw", "roll"),
    ) -> None:
        if thresholds is None:
            thresholds = HeadPoseThresholds()
        elif isinstance(thresholds, Mapping):
            thresholds = HeadPoseThresholds(
                yaw=thresholds.get("yaw", 20.0),
                pitch=thresholds.get("pitch", 20.0),
                roll=thresholds.get("roll", 20.0),
            )
        self.thresholds = thresholds
        if len(pose_order) != 3:
            raise ValueError("pose_order must describe three axes")
        pose_keys = {"pitch", "yaw", "roll"}
        if set(pose_order) != pose_keys:
            raise ValueError("pose_order must contain pitch, yaw, and roll")
        self.pose_order = tuple(pose_order)

    def classify(self, yaw: float, pitch: float, roll: float) -> str:
        """
        Return a coarse orientation label for the provided angles.
        """
        t = self.thresholds
        if yaw <= -t.yaw:
            return "Looking Left"
        if yaw >= t.yaw:
            return "Looking Right"
        if pitch >= t.pitch:
            return "Looking Up"
        if pitch <= -t.pitch:
            return "Looking Down"
        if roll >= t.roll:
            return "Tilting Left"
        if roll <= -t.roll:
            return "Tilting Right"
        return "Straight"

    def classify_sequence(self, pose: Iterable[float]) -> str:
        """
        Classify an angle sequence that follows the configured pose order.
        """
        pitch, yaw, roll = self._ordered_pose(pose)
        return self.classify(yaw=yaw, pitch=pitch, roll=roll)

    def _ordered_pose(self, pose: Iterable[float]) -> Tuple[float, float, float]:
        values = list(pose)
        if len(values) != 3:
            raise ValueError("Expected pose sequence with three values")
        axis_map = dict(zip(self.pose_order, values))
        return (
            float(axis_map["pitch"]),
            float(axis_map["yaw"]),
            float(axis_map["roll"]),
        )
