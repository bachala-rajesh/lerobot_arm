# apriltags_localization

AprilTag-based robot localization. Detects 36h11 tags from camera images, estimates tag poses, and computes the robot's world position.

---

## Nodes

| File | Node name | Purpose |
|------|-----------|---------|
| `detect_apriltags.py` | `detect_apriltags_node` | Detects tags using `dt_apriltags` (Duckietown), publishes TF per tag |
| `apriltag_world_localizer.py` | `apriltag_world_localizer` | Reads known tag world positions from YAML + TF detections, outputs `world → camera` TF |
| `optimize_pose.py` | — | Refines robot pose from multiple tag detections using OpenCV PnP solvers |

---

## Launch files

| File | Purpose |
|------|---------|
| `detect_apriltag_ros_tf.launch.py` | Tag detection using `apriltag_ros` (3rd party) |
| `detect_apriltags_node_sim.launch.py` | Tag detection on simulation using `dt_apriltags` (Duckietown library) |
| `detect_apriltags_node_real.launch.py` | Tag detection on real camera using  `dt_apriltags` (Duckietown library)  |
| `apriltag_world_localizer.launch.py` | World localizer node only |
| `localize_apriltags.launch.py` | Full pipeline: detection + world localization |
| `optimize_pose.launch.py` | Pose optimization from multiple tags |
| `robot_to_tag_static_tf.launch.py` | Publish static TF from robot base to known tag position |

---

## Config files

| File | Purpose |
|------|---------|
| `tag_poses_in_world.yaml` | Known 3D positions of each tag in world frame |
| `real_apriltags_detections_config.yaml` | Detection params for real OAK-D camera |
| `sim_apriltags_detections_config.yaml` | Detection params for Gazebo sim |
| `dt_sim_apriltag_detections_config.yaml` | Detection params using dt_apriltags in sim |
| `sim_apriltags_global_location.yaml` | Tag world positions for sim |
| `optimize_pose_config.yaml` | PnP solver settings |
| `robot_to_tag_calibration.yaml` | Measured offset from robot base to reference tag |

---

## Dependencies

- [`apriltag_ros`](https://github.com/christianrauch/apriltag_ros) — 3rd party ROS2 AprilTag package
- [`lib-dt-apriltags`](https://github.com/duckietown/lib-dt-apriltags) — Duckietown detection library
- `tf2_ros`, `cv_bridge`, `sensor_msgs`, `geometry_msgs`
