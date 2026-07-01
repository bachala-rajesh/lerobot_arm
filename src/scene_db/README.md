# scene_db

SQLite-backed scene memory. Stores object detections (from VLM, AprilTag, YOLO) with 2D bboxes. The localizer fills in 3D world coordinates later.

Used as a Python library — imported directly by other nodes. No ROS2 node of its own.

---

## DB file location

The database file is **not inside this package**. It lives at:

```
~/.ros/scene_db/scene.db     (default)
```

Override with an environment variable:

```bash
export SCENE_DB_PATH=/your/custom/path/scene.db
```

The directory is created automatically on first use.

---

## Python API

```python
from scene_db import SceneDB

with SceneDB() as db:
    # Insert a detection (world coords filled in later)
    row_id = db.insert_detection(
        label="red_cup",
        bbox=(10, 20, 100, 120),
        image_size=(640, 480),
        detector="vlm",
        source_frame="oak_rgb_camera_optical_frame",
    )

    # Localizer fills in 3D coords
    db.update_world_coords(row_id, world_xyz=(0.3, -0.1, 0.5))

    # Query
    rows = db.query_by_label("red_cup", max_age_sec=60, require_3d=True)
    recent = db.query_recent(limit=20)
    pending = db.list_pending()          # rows still missing 3D coords
    total, pending_count = db.count()
```

---

## Files

| File | Purpose |
|------|---------|
| `scene_db/database.py` | `SceneDB` class and `Detection` dataclass |
| `scene_db/__init__.py` | Exports `SceneDB`, `Detection`, `DEFAULT_DB_PATH` |
| `scene_db/inspect_db.py` | CLI tool to inspect / clear the database |
| `config/scene_db.yaml` | Reserved for future params (retention, pruning) |

---

## CLI inspector

```bash
ros2 run scene_db inspect_db                   # 20 most recent rows
ros2 run scene_db inspect_db --label "cup"     # filter by label
ros2 run scene_db inspect_db --pending         # rows missing 3D coords
ros2 run scene_db inspect_db --count           # total + pending counts
ros2 run scene_db inspect_db --clear           # delete all rows (asks confirmation)
ros2 run scene_db inspect_db --db /tmp/x.db   # custom db file
```

---

## Schema

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Primary key |
| `label` | TEXT | Object name |
| `bbox_x1/y1/x2/y2` | INTEGER | Pixel bbox in source image |
| `image_width/height` | INTEGER | Source image size |
| `world_x/y/z` | REAL | 3D in world frame — NULL until localizer fills |
| `confidence` | REAL | Detector confidence, may be NULL |
| `source_frame` | TEXT | TF frame the bbox was taken from |
| `detector` | TEXT | `"vlm"`, `"yolo"`, `"apriltag"`, etc. |
| `detected_at` | REAL | Unix timestamp of detection |
| `localized_at` | REAL | Unix timestamp of 3D update — NULL while pending |
