#!/usr/bin/env python3

#TODO: add joint limits
#  JOINT_LIMITS = {                                                                                                                                                                     
#       "shoulder_pan":  (-1.5, 1.5),
#       "shoulder_lift": (-1.5, 1.5),                                                                                                                                                    
#       "elbow_flex":    (-1.5, 1.5),
#       "wrist_flex":    (-1.5, 1.5),                                                                                                                                                    
#       "wrist_roll":    (-1.5, 1.5),                                                                                                                                                    
#   }
                                                                                                                                                                                       
#   target = base_pos + noise                                                                                                                                                            
#   lo, hi = JOINT_LIMITS[joint]
#   target = max(lo, min(hi, target))   # clamp       

"""ROS 2 node that publishes JointTrajectory commands with Perlin-noise perturbations."""

from __future__ import annotations

import math
import random

import numpy as np
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from test_pkg.perlin_noise import perlin_noise

ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]

JOINTS_OFFSET: dict[str, int] = {}

for i, joint in enumerate(ARM_JOINTS):
    JOINTS_OFFSET[joint] = (i+1)  * 100
    





class PerlinNoiseNode(Node):
    """Publishes perlin-noise-perturbed joint trajectories at 50 Hz."""

    def __init__(self) -> None:
        super().__init__("perlin_noise_node")

        self.declare_parameter("publish_topic", "/arm_controller/joint_trajectory")
        self.declare_parameter("noise_amplitude", 0.005)
        self.declare_parameter("noise_frequency", 0.5)

        self._topic = str(self.get_parameter("publish_topic").value)
        self._amplitude = float(self.get_parameter("noise_amplitude").value)
        self._frequency = float(self.get_parameter("noise_frequency").value)
        self._current_positions: dict[str, float] = {}
        self._time = 0.0

        self._joint_state_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self._joint_state_callback,
            10,
        )

        self._traj_pub = self.create_publisher(
            JointTrajectory,
            self._topic,
            10,
        )

        # 50 Hz timer → period = 0.02 s
        self._timer = self.create_timer(0.02, self._timer_callback)

        self.get_logger().info(
            f"PerlinNoiseNode started. Publishing to {self._topic} at 50 Hz."
        )

    def _joint_state_callback(self, msg: JointState) -> None:
        for name, pos in zip(msg.name, msg.position):
            self._current_positions[name] = pos

    def _timer_callback(self) -> None:
        if not self._current_positions:
            self.get_logger().warn("No joint state received yet; skipping.")
            return
    

        traj_msg = JointTrajectory()
        traj_msg.header.stamp.sec = 0                                                                                                                                                        
        traj_msg.header.stamp.nanosec = 0
        traj_msg.joint_names = ARM_JOINTS

        point = JointTrajectoryPoint()

        # point.time_from_start = Duration(sec=0, nanosec=int(0.1 * 1e9))  # 100ms

        for i, joint in enumerate(ARM_JOINTS):
            base_pos = self._current_positions.get(joint, 0.0)
            noise = perlin_noise(self._amplitude, self._time, self._frequency, JOINTS_OFFSET[joint])
            target = base_pos + noise
            point.positions.append(target)
            point.velocities = [0.0] * len(ARM_JOINTS) 
            point.accelerations = [0.0] * len(ARM_JOINTS) 
            


        traj_msg.points.append(point)
        self._traj_pub.publish(traj_msg)

        self._time += 0.02



def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PerlinNoiseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
