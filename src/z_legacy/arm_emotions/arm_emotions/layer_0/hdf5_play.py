#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import h5py
import numpy as np
from typing import Any

from utilities import (
    YAMLParser,
    get_episode_and_filename,
    MotionType,
    Groups,
    Metadata,
    PathConfig,
)


class HDF5Play:
    def __init__(self, emotion: str, episode: int) -> None:
        self.hdf5_file = None  # opened lazily in open_file()

        yaml_parser = YAMLParser()
        self.emotions_list = yaml_parser.emotions_list

        # Validate emotion
        if emotion not in self.emotions_list:
            raise ValueError(
                f"Unknown emotion {emotion!r}. Valid options: {self.emotions_list}"
            )
        self.emotion = emotion
        self.episode = episode

        self.motion_dir = PathConfig.motion_dir_path
        self.emotion_dir = self.motion_dir / self.emotion
        self.hdf5_filename = f"episode_{self.episode:03d}.h5"
        self.hdf5_file_path = self.emotion_dir / self.hdf5_filename

        # Validate file exists
        if not self.hdf5_file_path.is_file():
            raise FileNotFoundError(
                f"Episode {self.episode} not found for emotion "
                f"{self.emotion!r} at {self.hdf5_file_path}"
            )

    def open_file(self) -> None:
        """Open the hdf5 file for reading + in-place metadata edits."""
        # "r+" preserves existing data and allows attribute updates.
        self.hdf5_file = h5py.File(self.hdf5_file_path, "r+")

    def close_file(self) -> None:
        """Close hdf5 file. If the in-file EMOTION attr no longer matches the
        current folder, move the file to the matching folder first."""
        if self.hdf5_file is None:
            return

        # the in-file EMOTION attr is the user's "intended" label.
        # If it differs from the folder we live in, move now before closing.
        target_emotion = self.hdf5_file.attrs[Metadata.EMOTION.value]
        if isinstance(target_emotion, bytes):
            target_emotion = target_emotion.decode()

        if target_emotion != self.emotion:
            self._relocate_to(target_emotion)
            return

        self.hdf5_file.close()
        self.hdf5_file = None

    def _relocate_to(self, new_emotion: str) -> None:
        """Internal: close, rename into new_emotion folder with a fresh episode
        number, sync the EPISODE attr inside the file, leave the file closed."""
        if new_emotion not in self.emotions_list:
            raise ValueError(
                f"Unknown emotion {new_emotion!r}. Valid options: {self.emotions_list}"
            )

        # must close before renaming
        self.hdf5_file.close()
        self.hdf5_file = None

        # pick a fresh episode number in the destination folder
        new_emotion_dir = self.motion_dir / new_emotion
        new_emotion_dir.mkdir(parents=True, exist_ok=True)
        new_episode, new_filename = get_episode_and_filename(new_emotion)
        new_path = new_emotion_dir / new_filename

        self.hdf5_file_path.rename(new_path)

        # episode number changed — sync it inside the file
        with h5py.File(new_path, "r+") as f:
            f.attrs[Metadata.EPISODE.value] = new_episode

        # update internal state so callers can read the final path/episode
        self.emotion = new_emotion
        self.episode = new_episode
        self.emotion_dir = new_emotion_dir
        self.hdf5_filename = new_filename
        self.hdf5_file_path = new_path

    # ---------- read access ----------

    def get_hdf5_file_path(self) -> Path:
        return self.hdf5_file_path

    def get_dataset(self, group: Groups) -> np.ndarray:
        """Read one full dataset into memory as a numpy array."""
        return self.hdf5_file[group.value][:]

    # ---------- metadata ----------

    def get_metadata(self, key: Metadata) -> Any:
        """Read a single metadata attribute."""
        return self.hdf5_file.attrs[key.value]

    def get_all_metadata(self) -> dict[str, Any]:
        """Return all metadata attributes as a plain dict."""
        return {k: self.hdf5_file.attrs[k] for k in self.hdf5_file.attrs}

    def modify_metadata(self, key: Metadata, value: Any) -> None:
        """Update a single metadata attribute in place.

        Note: changing Metadata.EMOTION does NOT move the file. The actual
        file move (if needed) happens lazily in close_file().
        """
        if key == Metadata.EMOTION and value not in self.emotions_list:
            raise ValueError(
                f"Unknown emotion {value!r}. Valid options: {self.emotions_list}"
            )
        self.hdf5_file.attrs[key.value] = value
