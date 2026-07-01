#!/usr/bin/env python3

from __future__ import annotations

import yaml
from pathlib import Path
import os
import h5py
import numpy as np
from enum import Enum
from datetime import datetime
from typing import Optional


# hardcoded yaml path TODO: remove
class PathConfig:
    home_path = Path(os.environ["HOME"])
    lerobot_ws = home_path / "workspaces/lerobot_ws/src"
    rel_yaml_config_path = "arm_emotions/config/record_motion.yaml"
    yaml_path = lerobot_ws / rel_yaml_config_path
    motion_dir_path = lerobot_ws / "motion_recordings"


class MotionType(str, Enum):
    TELEPORT = "teleport"
    EQUATION = "equation"


class UserRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Groups(str, Enum):
    ARM_POS = "arm_pos"
    GRIPPER_POS = "gripper_pos"
    ARM_VEL = "arm_vel"
    GRIPPER_VEL = "gripper_vel"
    POSE = "pose"
    TIMESTAMPS = "timestamps"


class Metadata(str, Enum):
    EPISODE = "episode"
    DURATION = "duration"
    EMOTION = "emotion"
    MOTION_BASIS = "motion_basis"
    USER_RATING = "user_rating"
    USER_COMMENT = "user_comment"
    JOINT_NAMES = "joint_names"
    CREATED_TIME = "created_time"


class YAMLParser:
    def __init__(self):
        self.emotions_list = []
        self.num_joints = None
        self.record_frequency = None
        self.parent_frame = None
        self.child_frame = None

        with open(PathConfig.yaml_path) as f:
            raw = yaml.safe_load(f)

        self.emotions_list = self.find_value(raw, "emotions")
        self.num_joints = self.find_value(raw, "num_joints")
        self.record_frequency = self.find_value(raw, "record_frequency")
        self.parent_frame = self.find_value(raw, "parent_frame")
        self.child_frame = self.find_value(raw, "child_frame")

        if (
            len(self.emotions_list) == 0
            or self.num_joints is None
            or self.record_frequency is None
            or self.parent_frame is None
            or self.child_frame is None
        ):
            raise ValueError(
                "Invalid YAML config: emotions_list or num_joints or record_frequency or parent_frame or child_frame is empty."
            )

    def find_value(self, data: dict, key: str) -> Optional:
        """Recursively find a value in a nested dictionary."""
        if key in data:
            return data[key]
        for value in data.values():
            if isinstance(value, dict):
                result = self.find_value(value, key)
                if result is not None:
                    return result
        return None

    def load_emotions_list(self) -> list:
        """Load the list of emotions from the YAML file."""
        return self.emotions_list

    def load_num_joints(self) -> int:
        """Load the number of joints from the YAML file."""
        return self.num_joints

    def load_record_frequency(self) -> int:
        """Load the record frequency from the YAML file."""
        return self.record_frequency

    def load_parent_child_frame(self) -> tuple:
        """Load the parent and child frame from the YAML file."""
        return self.parent_frame, self.child_frame


def get_episode_and_filename(emotion: str) -> str:
    """Get filename from folder name."""
    emotion_dir = PathConfig.motion_dir_path / emotion
    max_number = 0
    for item in emotion_dir.glob("episode_*.h5"):
        try:
            n = int(item.stem.split("_")[-1])
            max_number = max(max_number, n)
        except ValueError:
            pass

    episode = max_number + 1
    filename = f"episode_{episode:03d}.h5"
    return episode, filename


def check_episode_available(emotion, episode: int) -> bool:
    """Check if the episode number exists."""
    emotion_dir = PathConfig.motion_dir_path / emotion

    for item in emotion_dir.glob("episode_*.h5"):
        try:
            n = int(item.stem.split("_")[-1])
            if n == episode:
                return True
            else:
                continue
        except ValueError:
            pass
    return False


def list_episode_files(emotion: str) -> list[Path]:
    """Return a sorted list of all episode files for the given emotion.

    Returns an empty list if the emotion folder does not exist yet.
    Useful for verifier/exporter/play scripts that need to enumerate
    what's been recorded for a given emotion.
    """
    emotion_dir = PathConfig.motion_dir_path / emotion
    if not emotion_dir.is_dir():
        return []
    return sorted(emotion_dir.glob("episode_*.h5"))
