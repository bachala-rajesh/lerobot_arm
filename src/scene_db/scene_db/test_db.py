from database import SceneDB
db = SceneDB()
print(db.path)             # confirms file location
rid = db.insert_detection(
    label="big_cup",
    bbox=(10, 20, 100, 120),
    image_size=(1280, 720),
    detector="manual",
    source_frame="oak_rgb_camera_optical_frame",
)   
print("inserted id:", rid)
print(db.query_recent(5))
db.update_world_coords(rid, (0.3, -0.1, 0.5))
print(db.list_pending())   # should be empty now
db.close()
