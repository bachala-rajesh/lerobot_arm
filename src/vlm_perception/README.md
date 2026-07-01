# vlm_perception

ROS2 node that runs Qwen-VL (via Alibaba DashScope) on camera images and exposes the result as a ROS2 service.

---

## API key — required before running

This node calls the Alibaba DashScope API. Without a valid API key, it will fail on startup.

**Step 1** — Get a key at [dashscope.aliyuncs.com](https://dashscope.aliyuncs.com)

**Step 2** — Set it as an environment variable:

```bash
export DASHSCOPE_API_KEY=your_key_here
```

Add that line to your `~/.bashrc` so it persists across terminals.

**Step 3** — In `config/vlm.yaml`, leave `api_key` as `"DASHSCOPE_API_KEY"` (default). The node reads it from the env var automatically.

---

## Files

| File | Purpose |
|------|---------|
| `vlm_perception/vlm_node.py` | ROS2 node — subscribes to camera, exposes `/vlm/detect_objects` service |
| `vlm_perception/test_client.py` | CLI tool to call the service and print / visualise results |
| `config/vlm.yaml` | Node parameters (service name, resize, API key, scene_db flags) |
| `launch/vlm.launch.py` | Launch with `use_sim_time:=true/false` to switch sim vs real camera |

---

## Service

| Name | Type | Description |
|------|------|-------------|
| `/vlm/detect_objects` | `project_interfaces/srv/DetectObjects` | Send a text prompt, get back bboxes + description |

---

## Topics subscribed

| Topic (remapped in launch) | Type | Used when |
|---------------------------|------|-----------|
| `/oak/rgb/image_raw/compressed` | `CompressedImage` | Real robot |
| `/oak/rgb/image_raw` | `Image` | Gazebo sim |

---

## Launch

```bash
# Real robot
ros2 launch vlm_perception vlm.launch.py use_sim_time:=false

# Simulation
ros2 launch vlm_perception vlm.launch.py use_sim_time:=true
```

---

## Test client

```bash
# Call the service and print results
ros2 run vlm_perception test_client --prompt "What objects are on the table?"

# Also draw bboxes on a live camera frame
ros2 run vlm_perception test_client --prompt "Find objects" --show
```
