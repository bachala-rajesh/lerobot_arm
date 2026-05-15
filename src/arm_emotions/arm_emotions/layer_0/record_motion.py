#!/usr/bin/env python3
"""ROS 2 node that subscribes to /joint_states and prints the values."""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import tf2_ros
from tf2_ros import TransformException
from rclpy.duration import Duration
import tf_transformations
import numpy as np



class RecordMotion(Node):
    """Node that prints incoming JointState messages."""

    def __init__(self) -> None:
        super().__init__("record_motion")
        
        self.declare_parameter("parent_frame", "follower_base_link")
        self.declare_parameter("child_frame", "follower_gripper_link")
        self.declare_parameter("record_frequency", 50)
        self.declare_parameter("emotions", ["neutral"])

        
        self.emotions = self.get_parameter("emotions").get_parameter_value().string_array_value
        self.parent_frame = self.get_parameter("parent_frame").get_parameter_value().string_value
        self.child_frame = self.get_parameter("child_frame").get_parameter_value().string_value
        self.record_frequency = self.get_parameter("record_frequency").get_parameter_value().integer_value
        self.dt = 1.0 / self.record_frequency
        
        
        self.joint_pos_ = np.array([])
        self.joint_vel_ = np.array([])
        self.joint_names_ = np.array([])
        self.joint_names_status_ = False
        
        self.subscription_ = self.create_subscription(
            JointState,
            "joint_states",
            self.joint_states_callback,
            10,
        )
        
        self.tf_buffer_ = tf2_ros.Buffer()
        self.tf_listener_ = tf2_ros.TransformListener(self.tf_buffer_, self)
        
        self.timer_ = self.create_timer(self.dt, self.timer_callback)
        
        self.get_logger().info("Record motion node started")

    def joint_states_callback(self, msg: JointState) -> None:
        
        self.joint_pos_ = np.array(msg.position)
        self.joint_vel_ = np.array(msg.velocity)
        
        if not self.joint_names_status_:
            self.joint_names_ = np.array(msg.name)
            self.joint_names_status_ = True
            
        
    
        
        
    def timer_callback(self):
        """Print the current EE pose."""
        # self.get_ee_pose()
        self.get_logger().info(f"Emotions: {self.emotions}")
        self.timer_.cancel()
        
    
    def get_ee_pose(self):
        try:
            t = self.tf_buffer_.lookup_transform(
                self.parent_frame,
                self.child_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.05)
            )
        except TransformException as e:
            self.get_logger().error(f"TD lookup failed: {e}")
            return None
        
        # position
        x = t.transform.translation.x
        y = t.transform.translation.y
        z = t.transform.translation.z
        
        # orientation
        qx = t.transform.rotation.x 
        qy = t.transform.rotation.y 
        qz = t.transform.rotation.z 
        qw = t.transform.rotation.w 
        
        roll, pitch, yaw = tf_transformations.euler_from_quaternion([qx, qy, qz, qw])
        
        self.get_logger().info(
            f"EE: x {x}, y {y}, z {z}, roll {roll}, pitch {pitch}, yaw {yaw}"
        )


def main(args: list[str] | None = None) -> None:
    """Entry point for the joint_state_printer node."""
    rclpy.init(args=args)
    node = RecordMotion()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
