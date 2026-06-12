"""scene_db — SQLite-backed scene memory.

Typical use:
    from scene_db import SceneDB
    with SceneDB() as db:
        row_id = db.insert_detection(label="red cube", bbox=(10,20,30,40),
                                     image_size=(640,480))
        db.update_world_coords(row_id, (0.3, -0.1, 0.5))
"""
from scene_db.database import SceneDB, Detection, DEFAULT_DB_PATH

__all__ = ["SceneDB", "Detection", "DEFAULT_DB_PATH"]
