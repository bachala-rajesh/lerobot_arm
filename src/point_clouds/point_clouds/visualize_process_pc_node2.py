#!/usr/bin/env python3

"""
📌 Live ROS2 PointCloud2 Visualizer using Open3D and threading

This script subscribes to a PointCloud2 topic (e.g., /oakd/depth/points) in ROS2,
processes the incoming point cloud data, and displays it in real-time using Open3D.

🧠 Features:
- Subscribes to ROS2 PointCloud2 messages.
- Converts ROS PointCloud2 to NumPy using ros2_numpy.
- Filters out invalid points (NaNs or infs).
- Downsamples point cloud using voxel grid filtering.
- Displays the processed point cloud live in an Open3D visualizer.
- Visualizer runs in a background thread (`VisualizerThread`) using `threading.Thread`.

✅ Technologies Used:
- ROS 2 (rclpy)
- Open3D
- ros2_numpy
- Python threading

👨‍💻 Usage:
- Ensure a PointCloud2 publisher (e.g., from OAK-D or Realsense) is active on `/oak/points`.
- Run this script inside a ROS 2 environment with required dependencies.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
import ros2_numpy as rnp
import open3d as o3d
import numpy as np
import threading
import time


class VisualizerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.lock = threading.Lock()
        self.points = np.random.rand(100, 3)
        self.colors = np.ones((100, 3))
        self.running = True

    def update(self, xyz: np.ndarray, rgb: np.ndarray):
        with self.lock:
            self.points = xyz
            self.colors = rgb

    def run(self):
        self.pcd = o3d.geometry.PointCloud()
        self.pcd.points = o3d.utility.Vector3dVector(self.points)
        self.pcd.colors = o3d.utility.Vector3dVector(self.colors)

        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window("Open3D Visualizer", width=800, height=600)
        self.vis.get_render_option().point_size = 5.0
        self.vis.add_geometry(self.pcd)

        while self.running:
            with self.lock:
                self.pcd.points = o3d.utility.Vector3dVector(self.points)
                self.pcd.colors = o3d.utility.Vector3dVector(self.colors)

            self.vis.update_geometry(self.pcd)
            self.vis.poll_events()
            self.vis.update_renderer()
            time.sleep(0.03)

        self.vis.destroy_window()

    def stop(self):
        self.running = False


class PointCloudSubscriber(Node):
    def __init__(self, visualizer: VisualizerThread):
        super().__init__("pcd_subscriber")
        self.visualizer = visualizer
        self._qos_profile = rclpy.qos.QoSProfile(depth=1)
        self._qos_profile.reliability = rclpy.qos.ReliabilityPolicy.BEST_EFFORT
        self.subscription = self.create_subscription(
            PointCloud2, "/oak/points", self.callback, self._qos_profile
        )
        self.get_logger().info("Subscribed to /oak/points")

    def callback(self, msg: PointCloud2):
        pc_array = rnp.numpify(msg).reshape(-1)
        xyz = np.stack([pc_array["x"], pc_array["y"], pc_array["z"]], axis=-1)

        mask = np.isfinite(xyz).all(axis=1)
        xyz = xyz[mask]

        rgb_flat = pc_array["rgb"].view(np.uint32)[mask]
        r = ((rgb_flat >> 16) & 0xFF).astype(np.uint8)
        g = ((rgb_flat >> 8) & 0xFF).astype(np.uint8)
        b = (rgb_flat & 0xFF).astype(np.uint8)
        rgb = np.stack([r, g, b], axis=-1) / 255.0

        # Downsample using Open3D
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(xyz)
        pcd.colors = o3d.utility.Vector3dVector(rgb)

        # down = pcd.voxel_down_sample(voxel_size=0.05)

        # points = np.asarray(down.points)
        # colors = np.asarray(down.colors)
        points = np.asarray(pcd.points)
        colors = np.asarray(pcd.colors)

        self.visualizer.update(points, colors)


def main():
    rclpy.init()
    vis_thread = VisualizerThread()
    vis_thread.start()

    node = PointCloudSubscriber(vis_thread)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        vis_thread.stop()
        vis_thread.join()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
