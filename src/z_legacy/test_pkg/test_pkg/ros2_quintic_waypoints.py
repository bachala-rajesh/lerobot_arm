#!/usr/bin/env python3
"""ROS 2 node that generates quintic polynomial trajectories and publishes JointTrajectory messages."""

from __future__ import annotations

import numpy as np
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from test_pkg.quintic_generator import quintic_generator, anticipation_trajectory, follow_through


ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]



class TestQuinticWaypoints(Node):
    """Node that subscribes to joint states and publishes quintic trajectories."""

    def __init__(self) -> None:
        super().__init__("test_quintic_waypoints")

        # Parameters
        self.declare_parameter("trajectory_duration", 5.0)
        self.declare_parameter("timer_period_sec", 5.0)
        self.declare_parameter("target_positions", [0.0, 0.0, 0.0, 0.0, 0.0])
        self.declare_parameter("publish_topic", "/arm_controller/joint_trajectory")

        self._traj_duration = float(self.get_parameter("trajectory_duration").value)
        self._timer_period = float(self.get_parameter("timer_period_sec").value)
        self._target_positions = list(self.get_parameter("target_positions").value)
        self._publish_topic = str(self.get_parameter("publish_topic").value)

        # Current joint state storage
        self._current_positions: dict[str, float] = {}

        # Subscriber
        self._joint_state_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self._joint_state_callback,
            10,
        )

        # Publisher
        self._traj_pub = self.create_publisher(
            JointTrajectory,
            self._publish_topic,
            10,
        )

        # Timer
        self._timer = self.create_timer(0.1, self._timer_callback)

        self.get_logger().info(
            f"TestQuinticWaypoints started. Publishing to {self._publish_topic} "
            f"every {self._timer_period}s with trajectory duration {self._traj_duration}s."
        )

    def _joint_state_callback(self, msg: JointState) -> None:
        """Store latest joint positions from /joint_states."""
        for name, pos in zip(msg.name, msg.position):
            self._current_positions[name] = pos

    def _timer_callback(self) -> None:
        """Generate and publish a quintic trajectory to the target positions."""
        if not self._current_positions:
            self.get_logger().warn("No joint state received yet; skipping trajectory generation.")
            return

        # Build start positions in the expected joint order
        start_positions = []
        target_positions = []
        d_target = -0.3
        for i, joint in enumerate(ARM_JOINTS):
            if joint not in self._current_positions:
                self.get_logger().warn(f"Joint {joint} not found in /joint_states; skipping.")
                return
            start_positions.append(self._current_positions[joint])
            target_positions.append(self._target_positions[i] + d_target)



        dt = 0.02
        foolow_pos_status = True
        omega = 4.0
        zeta = 0.4
        v_end = 0.3
        traj_points: dict[str, dict[str, list[float]]] = {}
        for i, joint in enumerate(ARM_JOINTS):
            pos, vel, acc, times = follow_through(
                                                start = start_positions[i],
                                                goal = target_positions[i],
                                                T = self._traj_duration,
                                                dt = dt,
                                                omega = omega,
                                                zeta = zeta,
                                                v_end = v_end,  
                                    )
            if foolow_pos_status:
                vel[-1] = 0.0
                acc[-1] = 0.0
                
            traj_points[joint] = {
                "pos": pos,
                "vel": vel,
                "accel": acc,
                "time": times,
            }
            
        jnt_traj_msg = JointTrajectory()
        # jnt_traj_msg.header.stamp = self.get_clock().now().to_msg()
        jnt_traj_msg.joint_names = ARM_JOINTS
        
        # Generate quintic trajectory for each joint
        n_steps = len(traj_points[ARM_JOINTS[0]]["pos"])
        for i in range(n_steps):
            jp = JointTrajectoryPoint()
            for joint in ARM_JOINTS:
                jp.positions.append(traj_points[joint]["pos"][i])
                jp.velocities.append(traj_points[joint]["vel"][i])
                jp.accelerations.append(traj_points[joint]["accel"][i])
            t_sec = traj_points[joint]["time"][i]
            jp.time_from_start = Duration(sec=int(t_sec), nanosec=int((t_sec - int(t_sec)) * 1e9))
            jnt_traj_msg.points.append(jp)
            
            
        # publish trajectory
        self._traj_pub.publish(jnt_traj_msg)
        self._timer.cancel()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TestQuinticWaypoints()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down due to keyboard interrupt.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
