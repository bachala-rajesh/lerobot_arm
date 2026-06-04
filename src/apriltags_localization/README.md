# 🧭 apriltags_localization

AprilTag-based localization package for a mobile robot.

---

## 📦 Overview
This package enables the detection of multiple AprilTags and localization of robot by optimizing its pose.
It integrates the third-party ROS 2 package [`apriltag_ros`](https://github.com/christianrauch/apriltag_ros) and the library [`lib-dt-apriltags`](https://github.com/duckietown/lib-dt-apriltags/tree/daffy) for AprilTag detection.  
Custom scripts are used to perform enhanced robot pose estimation and optimization.

---

## 🧠 Features
- 🔍 Detect multiple AprilTags using calibrated camera inputs
- 🧮 Optimize tag pose using reprojection + PnP techniques
- 🔁 Publish transforms using `tf2`


---

## Key Scripts
detect_apriltags.py
- Detects multiple AprilTags in the image stream
- Publishes their transforms relative to the camera frame
- Uses Duckietown's `lib-dt-apriltags` for detection

optimize_pose.py
- Refines the robot's pose using multiple detected tags
- Solves for the best-fit pose using OpenCV's PnP solvers (e.g., EPnP, Iterative)


---

## 🚀 Launch Options

### Apriltag detection only (with TF publishing)
##### 1. Detection of april tags using 3rd party ros2 package `apriltag_ros`

```bash
ros2 launch apriltags_localization detection_april_tags_tf.launch.py
```

##### 2. Detection of april tags using duckietown library `lib-dt-apriltags`

```bash
ros2 launch apriltags_localization dt_detection_apriltags_tf.launch.py
'''

### To optimize the robot's pose from data of multiple april tags.

```bash
ros2 launch apriltags_localization optimize_pose.launch.py

```bash
ros2 launch apriltags_localization localize_apriltags.launch.py
'''


---
📸 Media
(Images and videos will be added soon)

