#!/usr/bin/env python3
"""SQLite wrapper for the scene memory.

Schema (one table `detections`):

    id              INTEGER PRIMARY KEY
    label           TEXT     - object name from VLM/YOLO/AprilTag
    bbox_x1..y2     INTEGER  - pixel bbox in the source image
    image_width/image_height   INTEGER  - source image dims (for re-scaling later)
    world_x/y/z     REAL     - 3D in world frame (NULL until localizer fills)
    confidence      REAL     - detector confidence, may be NULL
    source_frame    TEXT     - tf frame the bbox was taken from
    detector        TEXT     - "vlm", "yolo", "apriltag", ...
    detected_at     REAL     - unix time when row inserted
    localized_at    REAL     - unix time when world_* was set (NULL while pending)

A row is "pending localization" while world_x IS NULL.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_DB_PATH: Path = Path(
    os.environ.get("SCENE_DB_PATH", str(Path.home() / "workspaces" / "lerobot_ws" / "src" / "scene_db" / "scene.db"))
)


# ---------------------------------------------------------------- record type
@dataclass
class Detection:
    """One row from the `detections` table."""
    id: int
    label: str
    bbox: tuple[int, int, int, int]      # x1, y1, x2, y2
    image_size: tuple[int, int]          # width, height
    world_xyz: tuple[float, float, float] | None
    confidence: float | None
    source_frame: str | None
    detector: str | None
    detected_at: float
    localized_at: float | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Detection":
        wx, wy, wz = row["world_x"], row["world_y"], row["world_z"]
        return cls(
            id=row["id"],
            label=row["label"],
            bbox=(row["bbox_x1"], row["bbox_y1"], row["bbox_x2"], row["bbox_y2"]),
            image_size=(row["image_width"], row["image_height"]),
            world_xyz=None if wx is None else (wx, wy, wz),
            confidence=row["confidence"],
            source_frame=row["source_frame"],
            detector=row["detector"],
            detected_at=row["detected_at"],
            localized_at=row["localized_at"],
        )


# ---------------------------------------------------------------- schema
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS detections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    label         TEXT    NOT NULL,
    bbox_x1       INTEGER NOT NULL,
    bbox_y1       INTEGER NOT NULL,
    bbox_x2       INTEGER NOT NULL,
    bbox_y2       INTEGER NOT NULL,
    image_width   INTEGER NOT NULL,
    image_height  INTEGER NOT NULL,
    world_x       REAL,
    world_y       REAL,
    world_z       REAL,
    confidence    REAL,
    source_frame  TEXT,
    detector      TEXT,
    detected_at   REAL    NOT NULL,
    localized_at  REAL
);
CREATE INDEX IF NOT EXISTS idx_label        ON detections(label);
CREATE INDEX IF NOT EXISTS idx_detected_at  ON detections(detected_at);
CREATE INDEX IF NOT EXISTS idx_pending      ON detections(world_x);
"""


# ---------------------------------------------------------------- main class
class SceneDB:
    """Thread-safe SQLite-backed scene memory.

    Use as a context manager or call .close() yourself.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._path: Path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # check_same_thread=False + our own lock → safe across ROS callback threads
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()

        # WAL mode: readers don't block writers — nice for ROS where many
        # nodes may read while one writes.
        with self._lock:
            self._conn.executescript("PRAGMA journal_mode=WAL;")
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.commit()

    # ------------------------------------------------ context manager
    def __enter__(self) -> "SceneDB":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @property
    def path(self) -> Path:
        return self._path

    # ------------------------------------------------ writes
    def insert_detection(
        self,
        label: str,
        bbox: tuple[int, int, int, int],
        image_size: tuple[int, int],
        confidence: float | None = None,
        source_frame: str | None = None,
        detector: str | None = None,
        detected_at: float | None = None,
    ) -> int:
        """Insert one detection. Returns the new row id."""
        x1, y1, x2, y2 = bbox
        w, h = image_size
        t = detected_at if detected_at is not None else time.time()

        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO detections
                    (label, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                     image_width, image_height,
                     confidence, source_frame, detector, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (label, x1, y1, x2, y2, w, h,
                 confidence, source_frame, detector, t),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def insert_detections_bulk(
        self,
        rows: Iterable[dict],
    ) -> list[int]:
        """Bulk insert. Each dict must have the same keys as insert_detection.
        Returns the inserted row ids (in order)."""
        ids: list[int] = []
        for r in rows:
            ids.append(self.insert_detection(**r))
        return ids

    def update_world_coords(
        self,
        row_id: int,
        world_xyz: tuple[float, float, float],
        localized_at: float | None = None,
    ) -> None:
        """Fill in the 3D world coords for a row."""
        wx, wy, wz = world_xyz
        t = localized_at if localized_at is not None else time.time()
        with self._lock:
            self._conn.execute(
                """
                UPDATE detections
                   SET world_x = ?, world_y = ?, world_z = ?, localized_at = ?
                 WHERE id = ?
                """,
                (wx, wy, wz, t, row_id),
            )
            self._conn.commit()

    def clear(self) -> None:
        """Delete every row. Useful between test runs."""
        with self._lock:
            self._conn.execute("DELETE FROM detections")
            self._conn.commit()

    # ------------------------------------------------ reads
    def list_pending(self, limit: int = 100) -> list[Detection]:
        """Detections that still need 3D localization (world_x IS NULL)."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM detections
                 WHERE world_x IS NULL
                 ORDER BY detected_at ASC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [Detection.from_row(r) for r in rows]

    def query_by_label(
        self,
        label: str,
        max_age_sec: float | None = None,
        limit: int = 10,
        require_3d: bool = False,
    ) -> list[Detection]:
        """Return rows matching label, newest first.

        max_age_sec: if set, only rows whose detected_at is within last N sec.
        require_3d:  if True, only rows that already have world_x/y/z.
        """
        clauses = ["label = ?"]
        params: list = [label]
        if max_age_sec is not None:
            clauses.append("detected_at >= ?")
            params.append(time.time() - max_age_sec)
        if require_3d:
            clauses.append("world_x IS NOT NULL")
        where = " AND ".join(clauses)
        sql = (
            f"SELECT * FROM detections WHERE {where} "
            f"ORDER BY detected_at DESC LIMIT ?"
        )
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [Detection.from_row(r) for r in rows]

    def query_recent(self, limit: int = 50) -> list[Detection]:
        """Most-recent detections regardless of label."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM detections ORDER BY detected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [Detection.from_row(r) for r in rows]

    def count(self) -> tuple[int, int]:
        """Returns (total_rows, pending_3d_rows)."""
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) FROM detections"
            ).fetchone()[0]
            pending = self._conn.execute(
                "SELECT COUNT(*) FROM detections WHERE world_x IS NULL"
            ).fetchone()[0]
        return int(total), int(pending)
