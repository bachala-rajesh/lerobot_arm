#!/usr/bin/env python3
"""Relay leader joint states to the follower arm controllers.

Data flow:
      → leader arm moves
      → /leader/joint_states                         (JointState)  ← cached here
      → timer fires at publish_rate_hz
      → /follower/arm_controller/joint_trajectory    (JointTrajectory)
      → /follower/gripper_controller/joint_trajectory (JointTrajectory)

The timer decouples the follower command rate from the joint_states publish
rate (~100 Hz in sim).  time_from_start is set to match the timer period so
the JTC has a well-defined motion horizon for each goal.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from typing import Dict, Optional

JOINT_ORDER = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper']

ARM_JOINTS = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll']
GRIPPER_JOINTS = ['gripper']


class LeaderFollowerRelay(Node):

    def __init__(self):
        super().__init__('leader_follower_relay')

        self.declare_parameter('leader_joint_states_topic', '/leader/joint_states')
        self.declare_parameter('follower_arm_topic',
                               '/follower/arm_controller/joint_trajectory')
        self.declare_parameter('follower_gripper_topic',
                               '/follower/gripper_controller/joint_trajectory')
        self.declare_parameter('publish_rate_hz', 30.0)

        leader_js_topic = self.get_parameter(
            'leader_joint_states_topic').get_parameter_value().string_value
        arm_topic = self.get_parameter(
            'follower_arm_topic').get_parameter_value().string_value
        gripper_topic = self.get_parameter(
            'follower_gripper_topic').get_parameter_value().string_value
        rate_hz = self.get_parameter(
            'publish_rate_hz').get_parameter_value().double_value

        # time_from_start matches the timer period so the JTC has one full
        # cycle to reach each goal before the next one arrives.
        self._dt = 1.0 / rate_hz

        self._latest_pos: Optional[Dict[str, float]] = None

        self._js_sub = self.create_subscription(
            JointState, leader_js_topic, self._joint_states_callback, 10)

        self._arm_pub = self.create_publisher(JointTrajectory, arm_topic, 10)
        self._gripper_pub = self.create_publisher(JointTrajectory, gripper_topic, 10)

        self.create_timer(self._dt, self._timer_callback)

        self.get_logger().info(
            f'Relaying {leader_js_topic} → {arm_topic}, {gripper_topic} '
            f'at {rate_hz:.0f} Hz (time_from_start={self._dt:.3f}s)')

    def _joint_states_callback(self, msg: JointState):
        """Cache the latest leader joint positions; warn once if names mismatch."""
        pos = dict(zip(msg.name, msg.position))
        missing = [j for j in JOINT_ORDER if j not in pos]
        if missing:
            self.get_logger().warn(
                f'Missing joints in /leader/joint_states: {missing}',
                throttle_duration_sec=2.0)
            return
        self._latest_pos = pos

    def _timer_callback(self):
        """Publish cached leader positions to follower controllers."""
        if self._latest_pos is None:
            return
        self._publish(self._arm_pub, ARM_JOINTS, self._latest_pos)
        self._publish(self._gripper_pub, GRIPPER_JOINTS, self._latest_pos)

    def _publish(self, pub, joint_names, pos_map):
        pt = JointTrajectoryPoint()
        pt.positions = [pos_map[j] for j in joint_names]
        # sec = int(self._dt)
        # pt.time_from_start = Duration(sec=sec, nanosec=int((self._dt - sec) * 1e9))

        traj = JointTrajectory()
        # Leave header.stamp at zero — JointTrajectoryController treats a zero
        # stamp as "start now using my own clock", avoiding wall-time vs
        # Gazebo sim-time mismatch that would queue the goal indefinitely.
        traj.joint_names = joint_names
        traj.points = [pt]
        pub.publish(traj)


def main(args=None):
    rclpy.init(args=args)
    node = LeaderFollowerRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
