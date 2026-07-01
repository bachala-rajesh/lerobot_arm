# oakd_camera

Launch and config files for the Luxonis OAK-D camera — real hardware and Gazebo simulation.

---

## Launch files

| File | Purpose |
|------|---------|
| `real.launch.py` | **Main launch** — starts OAK-D driver with compressed image transport |
| `sim_rsp.launch.py` | Robot state publisher for OAK-D URDF only (no driver) — used by Gazebo |
| `sim_pointcloud.launch.py` | Simulation: point cloud from Gazebo depth camera — used by Gazebo |

Legacy files (moved to `legacy/`): `oakd_camera_with_pointclouds.launch.py`, `oakd_pointclouds_stereo.launch.py`, `test_oakd_camera_launch.py`, `test_oakd_isaac_launch.py`

---

## Config files

| File | Purpose |
|------|---------|
| `oakd_camera_params.yaml` | OAK-D driver params: resolution, FPS, topics, compression |
| `test_oakd_camera_params.yaml` |  params for testing |

---

## Scripts

| File | Purpose |
|------|---------|
| `scripts/fix_camera_info.py` | Republishes `camera_info` with corrected frame_id for TF alignment |

---

## URDF

`urdf/oakd_camera_sim.urdf.xacro` — OAK-D camera model for Gazebo. Included by `so101_description` when sim mode is active.

---

## Notes

- Real camera uses **compressed transport** (`image_transport`) — raw 2.76 MB images cause Cyclone DDS silent drops.
- Frame: `oak_camera_optical_frame` → TF published by `depthai_descriptions`.