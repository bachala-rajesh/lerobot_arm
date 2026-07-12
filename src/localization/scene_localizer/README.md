# scene_localizer

Fills 3D world coordinates for pending detections in `scene_db`. Reads depth from OAK-D, back-projects each bbox center to a 3D point, then TF-transforms it to the world frame.

Depends on `apriltags_localization` to publish the `world → camera` TF.

---

## Node

| File | Node name | Purpose |
|------|-----------|---------|
| `localizer_node.py` | `localizer_node` | Polls `scene_db` for pending rows, fills `world_x/y/z` using depth + TF |

---

## Flow

```
scene_db.list_pending()
  → scale bbox center → depth image coords
  → NxN median depth patch
  → back-project pixel + depth → 3D in camera frame
  → TF transform → world frame
  → scene_db.update_world_coords(row_id, world_xyz)
```

---

## Launch

```bash
ros2 launch scene_localizer scene_localizer.launch.py
```

---

## Config (`config/scene_localizer.yaml`)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `depth_topic` | `/oak/stereo/image_raw` | Aligned depth image topic |
| `camera_info_topic` | `/oak/stereo/camera_info` | Camera intrinsics |
| `world_frame` | `world` | Target TF frame for 3D coords |
| `tick_hz` | `2.0` | How often to poll scene_db for pending rows |
| `batch_limit` | `20` | Max rows to process per tick |
| `patch_size` | `7` | NxN patch for median depth (reduces noise) |
| `min_depth` | `0.1` | Minimum valid depth in metres |
| `max_depth` | `5.0` | Maximum valid depth in metres |
| `tf_timeout_sec` | `0.2` | TF lookup timeout |

---

## Dependencies

- `scene_db` — reads pending rows and writes world coords
- `apriltags_localization` — must be running to supply `world → camera` TF
- `tf2_ros`, `tf2_geometry_msgs`, `cv_bridge`, `sensor_msgs`, `geometry_msgs`
