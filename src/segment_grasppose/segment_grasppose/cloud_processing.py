#!/usr/bin/env python3
"""Point-cloud cleaning — one place for all processing steps.

Pure numpy in, pure numpy out. No ROS, no AnyGrasp. Any node can import this.

For now: statistical outlier removal only. Crop, voxel downsample, and table
removal go here later, each as its own small function, with clean_cloud()
chaining the ones you turn on.

Offline check:
  python3 cloud_processing.py
"""

from __future__ import annotations

import numpy as np
import open3d as o3d


def remove_statistical_outliers(
    points: np.ndarray,
    colors: np.ndarray,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Drop points that sit far from their neighbors (floating specks).

    Open3D returns the kept indices; we use them to filter colors too, so the
    two arrays stay row-aligned.
    """
    if len(points) == 0:
        return points, colors

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    _, keep = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio
    )
    keep = np.asarray(keep, dtype=np.int64)
    return points[keep], colors[keep]


def _quat_to_z_axis(quat_xyzw: np.ndarray) -> np.ndarray:
    """Tag's local +Z axis expressed in the parent frame (unit vector).

    This is the 3rd column of the rotation matrix for quaternion (x, y, z, w).
    """
    x, y, z, w = (float(v) for v in quat_xyzw)
    axis = np.array(
        [2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)],
        dtype=np.float64,
    )
    return axis / np.linalg.norm(axis)


def remove_below_table(
    points: np.ndarray,
    colors: np.ndarray,
    tag_translation: np.ndarray,
    tag_quat_xyzw: np.ndarray,
    min_height: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Drop points below the table, using an AprilTag lying flat on the table.

    tag_translation : tag origin in the SAME frame as `points` (the cloud frame)
    tag_quat_xyzw   : tag orientation (x, y, z, w) in that frame
    min_height      : metres above the tag plane to keep.
                      0.0 = cut exactly at the table (removes below it).
                      0.01 = also strip the table surface (keep objects only).

    ponytail: assumes the tag's +Z points UP, out of the table. If it removes
    the wrong side (objects vanish, table stays), the tag faces the other way —
    negate the normal here, or flip min_height's sign.
    """
    if len(points) == 0:
        return points, colors

    p0 = np.asarray(tag_translation, dtype=np.float32)
    normal = _quat_to_z_axis(tag_quat_xyzw).astype(np.float32)
    height = (points - p0) @ normal  # signed distance to the table plane
    keep = height >= min_height
    return points[keep], colors[keep]


def clean_cloud(
    points: np.ndarray,
    colors: np.ndarray,
    tag_translation: np.ndarray | None = None,
    tag_quat_xyzw: np.ndarray | None = None,
    min_height: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Run the enabled cleaning steps, in order. Add steps here as you need them.

    Table removal runs only when a tag pose is given; otherwise it is skipped.
    """
    points, colors = remove_statistical_outliers(points, colors)
    if tag_translation is not None and tag_quat_xyzw is not None:
        points, colors = remove_below_table(
            points, colors, tag_translation, tag_quat_xyzw, min_height
        )
    return points, colors


def _selfcheck() -> None:
    """A dense blob plus a few far specks -> specks must be dropped."""
    rng = np.random.RandomState(0)  # fixed seed: Math.random-free, repeatable
    blob = rng.normal(0.0, 0.01, size=(2000, 3)).astype(np.float32)
    specks = np.array([[5, 5, 5], [-5, -5, -5], [5, -5, 5]], dtype=np.float32)
    points = np.vstack([blob, specks])
    colors = np.zeros_like(points)

    out_pts, out_cols = clean_cloud(points, colors)
    assert len(out_pts) < len(points), "nothing was removed"
    assert out_pts.max() < 1.0, "a far speck survived"
    assert len(out_pts) == len(out_cols), "points and colors fell out of sync"
    print(f"clean_cloud OK: {len(points)} -> {len(out_pts)} points")


def _selfcheck_table() -> None:
    """Tag flat at origin, +Z up -> points with z<0 are 'below the table'."""
    pts = np.array(
        [[0, 0, 1.0], [0, 0, 0.5], [0, 0, -0.5], [0, 0, -1.0]], dtype=np.float32
    )
    cols = np.zeros_like(pts)
    trans = np.array([0, 0, 0], dtype=np.float32)
    quat = np.array([0, 0, 0, 1], dtype=np.float32)  # identity -> normal = +Z

    out_pts, _ = remove_below_table(pts, cols, trans, quat, min_height=0.0)
    assert len(out_pts) == 2, out_pts
    assert (out_pts[:, 2] >= 0).all(), "a below-table point survived"

    # a 180-deg-about-X tag flips the normal to -Z: now z>0 is 'below'
    flip = np.array([1, 0, 0, 0], dtype=np.float32)
    assert _quat_to_z_axis(flip)[2] < 0, "normal did not flip"
    print("remove_below_table OK")


if __name__ == "__main__":
    _selfcheck()
    _selfcheck_table()
