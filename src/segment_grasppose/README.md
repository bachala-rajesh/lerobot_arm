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
| `segment_grasppose/sam2_view_node.py` | Live SAM2 viewer — centre-point prompt, shows mask overlay |
| `segment_grasppose/sam2_scene_node.py` | Live SAM2 viewer — bbox from scene_db, shows mask overlay |
| `test_sam2.py` | Standalone SAM2 test on one image file |
| `test_client.py` | CLI test client — calls service with bboxes or label |

---

## SAM2 viewer node

Subscribes to an image topic, runs SAM2 (one centre-point prompt) on the latest
frame at `rate_hz`, and shows the mask overlay in an OpenCV window **and** on the
`sam2_overlay` image topic.

```bash
ros2 run segment_grasppose sam2_view_node
ros2 run segment_grasppose sam2_view_node --ros-args -p image_topic:=/oak/rgb/image_raw -p rate_hz:=2.0
# headless: turn off the window, view the topic instead
ros2 run segment_grasppose sam2_view_node --ros-args -p display:=false
ros2 run rqt_image_view rqt_image_view /sam2_view_node/sam2_overlay
```

Needs `torchvision` installed (SAM2 dependency).

---

## SAM2 scene node

Same idea as the viewer, but the prompt is the **first (most-recent) object bbox
from `scene_db`** instead of a centre point. Shows the mask + bbox + label in a
window. The scene_db must be populated first (run the VLM / localizer node).

```bash
ros2 run segment_grasppose sam2_scene_node
ros2 run segment_grasppose sam2_scene_node --ros-args -p image_topic:=/oak/rgb/image_raw -p rate_hz:=1.0
```

Needs `torchvision` and a populated `scene_db`.

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
