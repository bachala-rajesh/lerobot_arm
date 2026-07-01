# segment_grasppose

Grasp pose estimation node using SAM2 + AnyGrasp pipeline.

**Status: stub** — pipeline structure is complete but SAM2 and AnyGrasp models are not wired in yet. See TODO sections in `segment_grasppose_node.py`.

---

## Node: `segment_grasppose_node`

### Topics subscribed

| Topic | Type | Purpose |
|-------|------|---------|
| `/oak/rgb/image_raw` | `sensor_msgs/Image` | RGB frame for SAM2 segmentation |
| `/oak/points` | `sensor_msgs/PointCloud2` | Organized point cloud for AnyGrasp |

### Service

| Name | Type | Description |
|------|------|-------------|
| `/segment_grasppose/find_grasp_pose` | `project_interfaces/srv/FindGraspPose` | Send bboxes or object label, get back ranked grasp poses |

---

## Pipeline

```
Request (bboxes_xyxy OR object_label)
  │
  ├─ if object_label → query scene_db for latest bbox   [TODO: wire]
  │
  ▼
SAM2(image, bboxes) → mask (H, W bool)                  [TODO: wire]
  │
  ▼
Filter PointCloud2 by mask → masked points (N, 3)
  │
  ▼
AnyGrasp(masked_pc) → ranked grasp poses                [TODO: wire]
  │
  ▼
Response: success, message, grasp_poses[]
```

---

## Files

| File | Purpose |
|------|---------|
| `segment_grasppose/segment_grasppose_node.py` | Main node |
| `test_client.py` | CLI test client — calls service with bboxes or label |

---

## Launch

No launch file yet. Run directly:

```bash
ros2 run segment_grasppose segment_grasppose_node
```

---

## Test client

```bash
# Test with direct bboxes
ros2 run segment_grasppose test_client

# The client runs two tests automatically:
#   Test A — passes bboxes directly: [100, 100, 300, 300]
#   Test B — passes object_label="cup" (scene_db lookup, stubbed)
```

---

## Dependencies

- `project_interfaces` — `FindGraspPose` service
- `cv_bridge`, `sensor_msgs`, `geometry_msgs`, `rclpy`
- SAM2 (not yet installed — see project AnyGrasp install notes)
- AnyGrasp SDK (installed — see `memory/projects/project_anygrasp_install.md`)
