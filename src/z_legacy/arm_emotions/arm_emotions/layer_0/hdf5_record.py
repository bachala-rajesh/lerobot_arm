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

from utilities import (
    YAMLParser,
    get_episode_and_filename,
    check_episode_available,
    MotionType,
    UserRating,
    Groups,
    Metadata,
    PathConfig,
)


class HDF5Record:
    def __init__(
        self, emotion: str, motion_type: MotionType = MotionType.TELEPORT
    ) -> None:
        self.motion_type = motion_type
        self.recording = False
        self.hdf5_file = None  # opened lazily in start_record()

        yaml_parser = YAMLParser()
        self.emotions_list = yaml_parser.emotions_list
        self.num_joints = yaml_parser.num_joints

        # Validate emotion
        if emotion not in self.emotions_list:
            raise ValueError(
                f"Unknown emotion {emotion!r}. Valid options: {self.emotions_list}"
            )
        self.emotion = emotion

        self.motion_dir = PathConfig.motion_dir_path
        self.emotion_dir = PathConfig.motion_dir_path / self.emotion

        self.emotion_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created {self.emotion} folder at: {self.emotion_dir}")

        # decide the path now, but don't open the file yet
        self.episode, self.hdf5_filename = get_episode_and_filename(self.emotion)
        self.hdf5_file_path = self.emotion_dir / self.hdf5_filename

    def get_hdf5_file_path(self) -> Path | None:
        """Get hdf5 file path."""
        hdf5_file_path = self.hdf5_file_path
        if hdf5_file_path.exists():
            return hdf5_file_path
        else:
            print(f"HDF5 file {hdf5_file_path} does not exist")
            return None

    def get_hdf5_file(self) -> h5py.File | None:
        """Get hdf5 file."""
        if self.hdf5_file is None:
            return None
        return self.hdf5_file

    def create_groups(self) -> None:
        """Create groups in hdf5 file. based on motion type."""
        # Create groups in hdf5 file. based on motion type
        if self.motion_type == MotionType.TELEPORT:
            self.create_resizable_dataset(Groups.ARM_POS.value, self.num_joints - 1)
            self.create_resizable_dataset(Groups.GRIPPER_POS.value, 1)
            self.create_resizable_dataset(Groups.ARM_VEL.value, self.num_joints - 1)
            self.create_resizable_dataset(Groups.GRIPPER_VEL.value, 1)
            self.create_resizable_dataset(Groups.POSE.value, 7)  # x, y, z, w, x, y, z
            self.create_resizable_dataset(Groups.TIMESTAMPS.value, 1)

        elif self.motion_type == MotionType.EQUATION:
            self.create_resizable_dataset(Groups.GRIPPER_POS.value, 1)
            self.create_resizable_dataset(Groups.POSE.value, 7)  # x, y, z, w, x, y, z
            self.create_resizable_dataset(Groups.TIMESTAMPS.value, 1)

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

    def append_frame(
        self,
        timestamp: float,
        pose: np.ndarray,
        gripper_pos: Optional[float] = None,
        arm_pos: Optional[np.ndarray] = None,
        arm_vel: Optional[np.ndarray] = None,
        gripper_vel: Optional[np.ndarray] = None,
    ) -> None:
        """Append one synchronized frame to all datasets in an episode group."""
        if not self.recording:
            return

        idx = self.hdf5_file[Groups.POSE.value].shape[0]

        if self.motion_type == MotionType.TELEPORT:
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

        elif self.motion_type == MotionType.EQUATION:
            self.hdf5_file[Groups.GRIPPER_POS.value].resize(idx + 1, axis=0)
            self.hdf5_file[Groups.POSE.value].resize(idx + 1, axis=0)
            self.hdf5_file[Groups.TIMESTAMPS.value].resize(idx + 1, axis=0)

            self.hdf5_file[Groups.GRIPPER_POS.value][idx, 0] = gripper_pos
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
        self.hdf5_file_path = None
        self.hdf5_file = None

    def start_record(self) -> None:
        """Open the hdf5 file, create datasets, and start recording."""
        self.hdf5_file = h5py.File(self.hdf5_file_path, "w")
        self.create_groups()
        self.recording = True

    def stop_record(self) -> None:
        """Stop recording."""
        self.recording = False
