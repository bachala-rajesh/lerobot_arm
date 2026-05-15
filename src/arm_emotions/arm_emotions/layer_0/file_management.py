#!/usr/bin/env python3

from __future__ import annotations

import yaml
from pathlib import Path
import os
import h5py
import numpy as np
from enum import Enum


# hardcoded yaml path TODO: remove
real_yaml_config_path = "arm_emotions/config/record_motion.yaml"

class MotionType(str, Enum):
    TELEPORT = "teleport"
    EQUATION= "equation"
    
class UserRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Groups(str, Enum):
    JOINT_POS = "joint_pos"
    JOINT_VEL = "joint_vel"
    GRIPPER = "gripper"
    POSE = "pose"
    TIMESTAMPS = "timestamps"
    
class Metadata(str, Enum):
    EPISODE: int = "episode"
    DURATION: float = "duration"
    EMOTION: str = "emotion"
    MOTION_BASIS: MotionType = "motion_basis"
    USER_RATING: UserRating = "user_rating"
    USER_COMMENT: str = "user_comment"
    
    

    


class HDFFileManagement:
    def __init__(self, emotion: str) -> None:
        home_path = Path(os.environ["HOME"])
        lerobot_ws = home_path / "workspaces/lerobot_ws/src"

        self.yaml_config_path = lerobot_ws / real_yaml_config_path
        self.emotion = emotion
        self.num_joints = 0

        # load yaml params
        folder_names, motion_dir_path, self.num_joints = self.load_yaml_params()
        self.motion_dir = lerobot_ws / motion_dir_path

        # create folder
        self.create_folder(self.motion_dir, self.emotion)

        # emotion folder path
        self.emotion_dir = self.motion_dir / self.emotion
        
        # get filename 
        self.episode =0
        self.filename = self.get_filename()
        
        # create hdf5 file
        self.hdf5_file_path = self.emotion_dir / f"{self.filename}.h5" 
        self.hdf5_file = None
        
        
    def load_yaml_params(self):
        """Extract ros__parameters from a YAML file."""
        with open(self.yaml_config_path) as f:
            raw = yaml.safe_load(f)

        folder_names = self.recursive_find_values(raw, key_name="emotions")
        motion_dir_path = self.recursive_find_values(raw, key_name="motion_dir")
        num_joints = self.recursive_find_values(raw, key_name="num_joints")
        
        return folder_names, motion_dir_path, num_joints

    def recursive_find_values(self, yaml_params: dict, key_name: str) -> list:
        """Find query value in YAML parameter dictionary recursively."""
        query_value = None
        for key, value in yaml_params.items():
            if key == key_name:
                query_value = value
                return query_value
            if isinstance(value, dict):
                result = self.recursive_find_values(value, key_name=key_name)
                return result

        return query_value

    def create_folder(self, path: Path, folder_name: str) -> None:
        """Create folder names in a given path."""
        (path / folder_name).mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {path / folder_name}")

    def get_filename(self) -> str:
        """Get filename from folder name."""
        if not self.emotion_dir.iterdir():
            self.episode = 0
            return "episode_001"

        max_number = 1
        for item in self.emotion_dir.iterdir():
            if item.is_file():
                filename = item.stem
                number = int(filename.split("_")[-1])
                max_number = max(max_number, number)

        self.episode = max_number + 1
        filename = f"episode_{max_number + 1:03d}"
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
        


    def create_resizable_dataset(self, name: str, cols: int | None,
                             dtype: str = "float64") -> h5py.Dataset:
        """Helper to create an empty resizable dataset."""
        if cols is None:
            shape: tuple[int, ...] = (0,)
            maxshape: tuple[int | None, ...] = (None,)
        else:
            shape = (0, cols)
            maxshape = (None, cols)
        self.hdf5_file.create_dataset(name, shape=shape, maxshape=maxshape, dtype=dtype, chunks=True)

    def create_groups(self) -> None:
        """Create groups in hdf5 file."""
        self.create_resizable_dataset(Groups.JOINT_POS.value, self.num_joints-1)
        self.create_resizable_dataset(Groups.JOINT_VEL.value, self.num_joints-1)
        self.create_resizable_dataset(Groups.GRIPPER.value, 1)
        self.create_resizable_dataset(Groups.POSE.value, 7)
        self.create_resizable_dataset(Groups.TIMESTAMPS.value, None)

    def append_frame(self, joints_pos: np.ndarray, gripper: float, joint_vel: np.ndarray, pose: np.ndarray, timestamp: float) -> None:
        """Append one synchronized frame to all datasets in an episode group."""
        idx = self.hdf5_file[Groups.JOINT_POS.value].shape[0]
        
        self.hdf5_file[Groups.JOINT_POS.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.JOINT_VEL.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.GRIPPER.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.POSE.value].resize(idx + 1, axis=0)
        self.hdf5_file[Groups.TIMESTAMPS.value].resize(idx + 1, axis=0)


        self.hdf5_file[Groups.JOINT_POS.value][idx, :] = joints_pos
        self.hdf5_file[Groups.JOINT_VEL.value][idx, :] = joint_vel
        self.hdf5_file[Groups.GRIPPER.value][idx, :] = gripper
        self.hdf5_file[Groups.POSE.value][idx, :] = pose
        self.hdf5_file[Groups.TIMESTAMPS.value][idx] = timestamp

    def add_metadata(self, duration: float, motion_basis: str = "teleport", user_rating: int = 1, user_comment: str = "") -> None:
        """Add metadata to hdf5 file."""
        self.hdf5_file.attrs[Metadata.EPISODE.value] = self.episode
        self.hdf5_file.attrs[Metadata.DURATION.value] = duration       
        self.hdf5_file.attrs[Metadata.EMOTION.value] = self.emotion 
        self.hdf5_file.attrs[Metadata.MOTION_BASIS.value] = motion_basis
        self.hdf5_file.attrs[Metadata.USER_RATING.value] = user_rating
        self.hdf5_file.attrs[Metadata.USER_COMMENT.value] = user_comment

    def close_file(self) -> None:
        """Close hdf5 file."""
        self.hdf5_file.close()
         
    def delete_file(self) -> None:
        """Delete hdf5 file."""
        self.hdf5_file_path.unlink(missing_ok=True)
        
def main() -> None:
    emotion = "curious"
    fm = HDFFileManagement(emotion)
    if fm.create_hdf5_file():
        joint_pos = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        gripper = 0.02
        joint_vel = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        pose = np.array([0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 1.0])
        timestamp = 0.06
        fm.append_frame(joint_pos, gripper, joint_vel, pose, timestamp)
        fm.add_metadata(duration=0.5, user_comment="aggressive")
        fm.close_file()
        
    
    # read file and print the content
    with h5py.File(fm.get_hdf5_file_path(), "r") as f:
        print(f.keys())
        print(f[Groups.JOINT_POS.value][0, :])
        print(f[Groups.JOINT_VEL.value][0, :])
        print(f[Groups.GRIPPER.value][0, :])
        print(f[Groups.POSE.value][0, :])
        print(f[Groups.TIMESTAMPS.value][0])
        print(f.attrs[Metadata.EPISODE.value])
        print(f.attrs[Metadata.DURATION.value])
        print(f.attrs[Metadata.EMOTION.value])
        print(f.attrs[Metadata.MOTION_BASIS.value])
        print(f.attrs[Metadata.USER_RATING.value])
        print(f.attrs[Metadata.USER_COMMENT.value])
        
        
    # delete file
    fm.delete_file()
        
        
        
    
        
    


if __name__ == "__main__":
    main()
