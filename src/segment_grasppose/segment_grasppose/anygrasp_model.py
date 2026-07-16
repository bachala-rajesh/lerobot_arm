#!/usr/bin/env python3
"""AnyGrasp wrapper — all the SDK setup lives here, nothing else needs to know.

No ROS inside. Import it from a node, or test it alone with a saved cloud.

Two things make the SDK work, and both happen in __init__:
  sys.path.append(SDK_DIR)   -> Python can find gsnet.so
  os.chdir(SDK_DIR)          -> the licence checker finds ./license/

The licence keys off the wired NIC MAC, not the folder, so SDK_DIR can be
anywhere the four licence files sit next to each other.

Self-check (loads the model, needs GPU + the SDK folder):
  python3 anygrasp_model.py           # print only
  python3 anygrasp_model.py --show    # also open the Open3D window
"""

from __future__ import annotations

import os
import sys
from argparse import Namespace

import numpy as np

# Folder holding gsnet.so, lib_cxx.so, license/, log/checkpoint_detection.tar.
SDK_DIR = os.environ.get(
    "ANYGRASP_SDK_DIR",
    "/workspaces/lerobot_ws/src/deep_learning_models/models/raw_models/anygrasp",
)

CHECKPOINT = "log/checkpoint_detection.tar"  # relative — resolved after chdir


class AnyGraspModel:
    """Loads AnyGrasp once, then answers predict() calls.

    Construction is slow (licence check + checkpoint load). Do it once at node
    startup, never per request.
    """

    def __init__(
        self,
        max_gripper_width: float = 0.05,
        gripper_height: float = 0.03,
        top_down_grasp: bool = False,
    ) -> None:
        if not os.path.isdir(SDK_DIR):
            raise FileNotFoundError(
                f"AnyGrasp SDK folder not found: {SDK_DIR}\n"
                f"Set ANYGRASP_SDK_DIR to the folder holding gsnet.so + license/."
            )

        # Order matters: path first, then chdir, then import.
        if SDK_DIR not in sys.path:
            sys.path.append(SDK_DIR)
        # ponytail: process-wide chdir, and it stays. The licence checker writes
        # ./.TimeRecord at runtime, so we must not wander off afterwards.
        os.chdir(SDK_DIR)

        from gsnet import AnyGrasp  # noqa: E402 — needs the two lines above

        # Namespace, not parse_args(): argparse would eat the node's ROS args.
        cfgs = Namespace(
            checkpoint_path=CHECKPOINT,
            max_gripper_width=max(0.0, min(0.1, max_gripper_width)),  # SDK caps at 0.1
            gripper_height=gripper_height,
            top_down_grasp=top_down_grasp,
            debug=False,
        )
        self._model = AnyGrasp(cfgs)
        self._model.load_net()

    def predict(
        self,
        points: np.ndarray,
        colors: np.ndarray,
        lims: list[float] | None = None,
    ):
        """Run grasp detection on one masked cloud.

        points: (N, 3) float32, metres, camera frame
        colors: (N, 3) float32, 0..1
        lims:   [xmin, xmax, ymin, ymax, zmin, zmax] workspace box.
                None -> derive from the points themselves.

        Returns the grasp group ranked best-first, or None if nothing was found.

        The SDK's get_grasp() also returns a cloud, but only when debug=True —
        otherwise it is None. Dropped rather than passed on: the caller already
        holds points+colors, so _show() rebuilds it and there is no None trap.
        """
        points = np.ascontiguousarray(points, dtype=np.float32)
        colors = np.ascontiguousarray(colors, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"points must be (N, 3), got {points.shape}")
        if colors.shape != points.shape:
            raise ValueError(f"colors {colors.shape} must match points {points.shape}")
        if len(points) == 0:
            return None

        if lims is None:
            lims = self.limits_from(points)

        gg, _ = self._model.get_grasp(
            points,
            colors,
            lims=lims,
            apply_object_mask=True,
            dense_grasp=False,
            collision_detection=True,
        )
        if gg is None or len(gg) == 0:
            return None
        return gg.nms().sort_by_score()

    @staticmethod
    def limits_from(points: np.ndarray, margin: float = 0.05) -> list[float]:
        """Workspace box around the points, padded by `margin` metres.

        A wrong box is the usual reason AnyGrasp returns zero grasps, so the
        default is simply "wherever the object already is".
        """
        lo = points.min(axis=0) - margin
        hi = points.max(axis=0) + margin
        return [
            float(lo[0]), float(hi[0]),
            float(lo[1]), float(hi[1]),
            float(lo[2]), float(hi[2]),
        ]


def _example_cloud() -> tuple[np.ndarray, np.ndarray]:
    """The SDK's own sample scene, unprojected to a cloud (same maths as demo.py)."""
    from PIL import Image

    data_dir = os.path.join(SDK_DIR, "example_data")
    colors = np.array(Image.open(f"{data_dir}/color.png"), dtype=np.float32) / 255.0
    depths = np.array(Image.open(f"{data_dir}/depth.png"))

    fx, fy, cx, cy, scale = 927.17, 927.37, 651.32, 349.62, 1000.0
    xmap, ymap = np.meshgrid(np.arange(depths.shape[1]), np.arange(depths.shape[0]))
    z = depths / scale
    x = (xmap - cx) / fx * z
    y = (ymap - cy) / fy * z

    keep = (z > 0) & (z < 1)
    points = np.stack([x, y, z], axis=-1)[keep].astype(np.float32)
    return points, colors[keep].astype(np.float32)


def _show(gg, points: np.ndarray, colors: np.ndarray) -> None:
    """Open3D window: the cloud plus every gripper, best one last."""
    import open3d as o3d

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    cloud.colors = o3d.utility.Vector3dVector(colors)

    # Camera looks down +Z, so the raw cloud renders upside down. Flip Z to
    # view it the way demo.py does. Display only — the poses are untouched.
    flip = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]])
    cloud.transform(flip)
    grippers = gg.to_open3d_geometry_list()
    for g in grippers:
        g.transform(flip)

    print("showing all grasps — close the window for the best one alone")
    o3d.visualization.draw_geometries([*grippers, cloud])
    o3d.visualization.draw_geometries([grippers[0], cloud])


def _self_check(show: bool = False) -> None:
    """Load the model and grasp the SDK's sample scene. Fails loudly if broken."""
    print(f"SDK_DIR = {SDK_DIR}")
    model = AnyGraspModel(top_down_grasp=True)
    print("model loaded — licence passed, checkpoint loaded")

    points, colors = _example_cloud()
    print(f"cloud        : {len(points)} points")

    # demo.py's hand-tuned box for this exact scene — a known-good input.
    gg = model.predict(points, colors, lims=[-0.19, 0.12, 0.02, 0.15, 0.0, 1.0])
    assert gg is not None, "no grasps on the SDK's own sample scene"
    print(f"grasps found : {len(gg)}")
    print(f"best score   : {gg[0].score:.3f}")

    # auto-lims must bound every point it was derived from
    lims = AnyGraspModel.limits_from(points)
    lo, hi = points.min(axis=0), points.max(axis=0)
    assert lims[0] < lo[0] and lims[1] > hi[0], "auto-lims does not bound x"
    assert lims[2] < lo[1] and lims[3] > hi[1], "auto-lims does not bound y"
    assert lims[4] < lo[2] and lims[5] > hi[2], "auto-lims does not bound z"
    print("self-check OK")

    if show:
        _show(gg, points, colors)


if __name__ == "__main__":
    _self_check(show="--show" in sys.argv)
