#!/usr/bin/env python3
"""Step 6: Multiple episodes in one file + iteration."""

from __future__ import annotations

import numpy as np
import h5py
from pathlib import Path


def create_resizable_dataset(group: h5py.Group, name: str, cols: int | None,
                             dtype: str = "float64") -> h5py.Dataset:
    """Helper to create an empty resizable dataset."""
    if cols is None:
        shape: tuple[int, ...] = (0,)
        maxshape: tuple[int | None, ...] = (None,)
    else:
        shape = (0, cols)
        maxshape = (None, cols)
    return group.create_dataset(name, shape=shape, maxshape=maxshape, dtype=dtype, chunks=True)


def append_frame(group: h5py.Group, joints: np.ndarray, gripper: float, timestamp: float) -> None:
    """Append one synchronized frame to all datasets in an episode group."""
    idx = group["joint_states"].shape[0]

    group["joint_states"].resize(idx + 1, axis=0)
    group["gripper"].resize(idx + 1, axis=0)
    group["timestamps"].resize(idx + 1, axis=0)

    group["joint_states"][idx, :] = joints
    group["gripper"][idx, :] = gripper
    group["timestamps"][idx] = timestamp


def main() -> None:
    file_path = Path("./z_temp/my_sixth_hdf5.h5")
    num_joints = 5

    # --- WRITE MULTIPLE EPISODES ---
    with h5py.File(file_path, "w") as f:
        f.attrs["robot_name"] = "so101"
        f.attrs["total_episodes"] = 0

        # Episode 0: 3 frames
        ep0 = f.create_group("episode_0")
        ep0.attrs["task"] = "pick_red_cube"
        create_resizable_dataset(ep0, "joint_states", num_joints)
        create_resizable_dataset(ep0, "gripper", 1)
        create_resizable_dataset(ep0, "timestamps", None)

        append_frame(ep0, np.array([0.1, 0.2, 0.3, 0.4, 0.5]), 0.02, 0.00)
        append_frame(ep0, np.array([0.2, 0.3, 0.4, 0.5, 0.6]), 0.01, 0.02)
        append_frame(ep0, np.array([0.3, 0.4, 0.5, 0.6, 0.7]), 0.00, 0.04)

        # Episode 1: 2 frames
        ep1 = f.create_group("episode_1")
        ep1.attrs["task"] = "place_red_cube"
        create_resizable_dataset(ep1, "joint_states", num_joints)
        create_resizable_dataset(ep1, "gripper", 1)
        create_resizable_dataset(ep1, "timestamps", None)

        append_frame(ep1, np.array([0.5, 0.4, 0.3, 0.2, 0.1]), 0.00, 0.00)
        append_frame(ep1, np.array([0.6, 0.5, 0.4, 0.3, 0.2]), 0.02, 0.02)

        # Update top-level metadata
        f.attrs["total_episodes"] = 2

    # --- ITERATE OVER ALL EPISODES ---
    print("--- Dataset summary ---")
    with h5py.File(file_path, "r") as f:
        print(f"Robot: {f.attrs['robot_name']}")
        print(f"Total episodes: {f.attrs['total_episodes']}\n")

        for key in f.keys():
            obj = f[key]
            if isinstance(obj, h5py.Group) and key.startswith("episode_"):
                frames = obj["joint_states"].shape[0]
                task = obj.attrs.get("task", "unknown")
                print(f"{key}: {frames} frames | task='{task}'")

    # --- LOAD ONE FULL EPISODE INTO MEMORY ---
    print("\n--- Load episode_0 into RAM ---")
    with h5py.File(file_path, "r") as f:
        ep0 = f["episode_0"]
        joints = ep0["joint_states"][:]
        gripper = ep0["gripper"][:]
        timestamps = ep0["timestamps"][:]

        print(f"joints shape: {joints.shape}")
        for i in range(len(timestamps)):
            print(f"  t={timestamps[i]:.2f} | {joints[i]} | gripper={gripper[i,0]:.3f}")


if __name__ == "__main__":
    main()
