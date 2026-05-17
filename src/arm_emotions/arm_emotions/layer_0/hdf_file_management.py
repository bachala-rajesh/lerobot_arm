#!/usr/bin/env python3

from __future__ import annotations

import yaml
from pathlib import Path
import os
import h5py
import numpy as np
from enum import Enum
from datetime import datetime


# hardcoded yaml path TODO: remove
real_yaml_config_path = "arm_emotions/config/record_motion.yaml"


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


class HDFFileManagement:
    def __init__(self, emotion: str) -> None:
        home_path = Path(os.environ["HOME"])
        lerobot_ws = home_path / "workspaces/lerobot_ws/src"
        yaml_path = lerobot_ws / real_yaml_config_path

        # Load YAML once
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)

        self.emotions_list = self._find_value(raw, "emotions")
        motion_dir_path    = self._find_value(raw, "motion_dir")
        self.num_joints    = self._find_value(raw, "num_joints")

        # Validate
        if emotion not in self.emotions_list:
            raise ValueError(
                f"Unknown emotion {emotion!r}. Valid options: {self.emotions_list}"
            )
        self.emotion = emotion

        self.motion_dir = lerobot_ws / motion_dir_path

        # create folder
        self.create_folder(self.motion_dir, self.emotion)

        # emotion folder path
        self.emotion_dir = self.motion_dir / self.emotion

        # get filename
        self.episode = 0
        self.filename = self.get_filename()

        # create hdf5 file
        self.hdf5_file_path = self.emotion_dir / f"{self.filename}.h5"
        self.hdf5_file = None
        self.create_hdf5_file()

        # recording
        self.recording = False

    @staticmethod
    def _find_value(d: dict, key: str):
        """Recursively find a key in a nested dict. Returns None if not found."""
        for k, v in d.items():
            if k == key:
                return v
            if isinstance(v, dict):
                result = HDFFileManagement._find_value(v, key)
                if result is not None:
                    return result
        return None


    def create_folder(self, path: Path, folder_name: str) -> None:
        """Create folder names in a given path."""
        (path / folder_name).mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {path / folder_name}")

    def get_filename(self) -> str:
        """Get filename from folder name."""
        max_number = 0
        for item in self.emotion_dir.glob("episode_*.h5"):
            try:
                n = int(item.stem.split("_")[-1])
                max_number = max(max_number, n)
            except ValueError:
                pass

        self.episode = max_number + 1
        filename = f"episode_{self.episode:03d}"
        return filename

    def create_hdf5_file(self) -> bool:
        """Open hdf5 file."""
        self.hdf5_file = h5py.File(self.hdf5_file_path, "w")
        if self.hdf5_file is None:
            return False

        self.create_groups()
        return True

    def get_hdf5_file_path(self) -> Path:
        """Get hdf5 file path."""
        return self.hdf5_file_path

    def create_resizable_dataset(
        self, name: str, cols: int | None, dtype: str = "float64"
    ) -> h5py.Dataset:
        """Helper to create an empty resizable dataset."""
        if cols is None:
            shape: tuple[int, ...] = (0,)
            maxshape: tuple[int | None, ...] = (None,)
        else:
            shape = (0, cols)
            maxshape = (None, cols)
        self.hdf5_file.create_dataset(
            name, shape=shape, maxshape=maxshape, dtype=dtype, chunks=True
        )

    def create_groups(self) -> None:
        """Create groups in hdf5 file."""
        self.create_resizable_dataset(Groups.ARM_POS.value, self.num_joints - 1)
        self.create_resizable_dataset(Groups.GRIPPER_POS.value, 1)
        self.create_resizable_dataset(Groups.ARM_VEL.value, self.num_joints - 1)
        self.create_resizable_dataset(Groups.GRIPPER_VEL.value, 1)
        self.create_resizable_dataset(Groups.POSE.value, 7)
        self.create_resizable_dataset(Groups.TIMESTAMPS.value, 1)

    def append_frame(
        self,
        arm_pos: np.ndarray,
        gripper_pos: float,
        arm_vel: np.ndarray,
        gripper_vel: np.ndarray,
        pose: np.ndarray,
        timestamp: float,
    ) -> None:
        """Append one synchronized frame to all datasets in an episode group."""
        if not self.recording:
            return

        idx = self.hdf5_file[Groups.ARM_POS.value].shape[0]

        self.hdf5_file[Groups.ARM_POS.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.GRIPPER_POS.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.ARM_VEL.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.GRIPPER_VEL.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.POSE.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.TIMESTAMPS.value].resize(idx + 1, axis=0)

        self.hdf5_file[Groups.ARM_POS.value][idx, :] = arm_pos
        self.hdf5_file[Groups.GRIPPER_POS.value][idx, 0] = gripper_pos
        self.hdf5_file[Groups.ARM_VEL.value][idx, :] = arm_vel
        self.hdf5_file[Groups.GRIPPER_VEL.value][idx, 0] = gripper_vel
        self.hdf5_file[Groups.POSE.value][idx, :] = pose
        self.hdf5_file[Groups.TIMESTAMPS.value][idx, 0] = timestamp

    def add_metadata(
        self,
        motion_basis: MotionType = MotionType.TELEPORT,
        duration: float = 0.0,
        user_rating: int = 1,
        user_comment: str = "",
        joint_names: list[str] = None,
    ) -> None:
        """Add metadata to hdf5 file."""
        self.hdf5_file.attrs[Metadata.EPISODE.value] = self.episode
        self.hdf5_file.attrs[Metadata.DURATION.value] = duration
        self.hdf5_file.attrs[Metadata.EMOTION.value] = self.emotion
        self.hdf5_file.attrs[Metadata.MOTION_BASIS.value] = motion_basis
        self.hdf5_file.attrs[Metadata.USER_RATING.value] = user_rating
        self.hdf5_file.attrs[Metadata.USER_COMMENT.value] = user_comment
        self.hdf5_file.attrs[Metadata.JOINT_NAMES.value] = joint_names
        self.hdf5_file.attrs[Metadata.CREATED_TIME.value] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def modify_metadata(self, attr: str, value: str | int | float | list[str]) -> bool:
        """Modify metadata in hdf5 file."""
        for member in list(Metadata):
            if member.value == attr:
                self.hdf5_file.attrs[member.value] = value
                print(f"Modified metadata {member.value} to {value}")
                return True
        print(f"Metadata {attr} not found")
        return False

    def close_file(self) -> None:
        """Close hdf5 file."""
        if self.hdf5_file is not None:
            self.hdf5_file.close()
            self.hdf5_file = None

    def delete_file(self, file: Path | None = None) -> None:
        """Delete hdf5 file."""
        if file is None:
            file = self.hdf5_file_path
        file.unlink(missing_ok=True)

    def start_record(self) -> None:
        """Start recording."""
        self.recording = True

    def stop_record(self) -> None:
        """Stop recording."""
        self.recording = False


    @classmethod
    def load_emotions_list(cls) -> list[str]:
        """Read just the list of valid emotions from the YAML config.
            No side effects — does not create folders or files."""
        home_path = Path(os.environ["HOME"])
        yaml_path = home_path / "workspaces/lerobot_ws/src" / real_yaml_config_path

        with open(yaml_path) as f:
            raw = yaml.safe_load(f)

        return cls._find_value(raw, "emotions")
