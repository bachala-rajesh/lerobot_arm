#!/usr/bin/env python3
"""ROS 2 node: Perlin-noise micro-motion using a rolling-window trajectory.

Each timer tick publishes a short trajectory covering the next WINDOW_POINTS
timesteps. The controller always has upcoming points queued, so a single late
or dropped publish never leaves the arm with no active trajectory.
"""

from __future__ import annotations

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

# Fill these in with your actual joint limits from joint_limits.yaml
JOINT_LIMITS: dict[str, tuple[float, float]] = {
    "shoulder_pan":  (-2.0, 2.0),
    "shoulder_lift": (-2.0, 2.0),
    "elbow_flex":    (-2.0, 2.0),
    "wrist_flex":    (-2.0, 2.0),
    "wrist_roll":    (-2.0, 2.0),
}

# Each joint samples noise at a different offset so they move independently
SEED_OFFSETS: dict[str, int] = {
    joint: (i + 1) * 100 for i, joint in enumerate(ARM_JOINTS)
}

DT = 0.02            # timer period and noise sample spacing (s) → 50 Hz
WINDOW_POINTS = 5    # points per published trajectory → 0.1 s lookahead


class PerlinNoiseRollingNode(Node):
    """Publishes rolling-window Perlin-noise trajectories at 50 Hz."""

    def __init__(self) -> None:
        super().__init__("perlin_noise_rolling_node")

        self.declare_parameter("publish_topic", "/arm_controller/joint_trajectory")
        self.declare_parameter("noise_amplitude", 0.005)
        self.declare_parameter("noise_frequency", 0.3)

        self._topic     = str(self.get_parameter("publish_topic").value)
        self._amplitude = float(self.get_parameter("noise_amplitude").value)
        self._frequency = float(self.get_parameter("noise_frequency").value)

        self._current_positions: dict[str, float] = {}
        self._noise_time = 0.0

        self._sub = self.create_subscription(
            JointState, "/joint_states", self._js_callback, 10
        )
        self._pub = self.create_publisher(JointTrajectory, self._topic, 10)
        self._timer = self.create_timer(DT, self._timer_callback)

        self.get_logger().info(
            f"PerlinNoiseRollingNode started → {self._topic} | "
            f"window={WINDOW_POINTS} pts ({WINDOW_POINTS * DT:.2f}s) | "
            f"amp={self._amplitude} rad | freq={self._frequency} Hz"
        )

    def _js_callback(self, msg: JointState) -> None:
        for name, pos in zip(msg.name, msg.position):
            self._current_positions[name] = pos

    def _timer_callback(self) -> None:
        if not self._current_positions:
            self.get_logger().warn(
                "No joint states received yet; skipping.",
                throttle_duration_sec=2.0,
            )
            return

        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        traj.joint_names = ARM_JOINTS

        # Snapshot base positions once for the entire window.
        # We do not re-read joint_states per point — the window represents
        # small offsets around the current held pose, not a moving target.
        base = {j: self._current_positions.get(j, 0.0) for j in ARM_JOINTS}

        for k in range(1, WINDOW_POINTS + 1):
            sample_time = self._noise_time + k * DT
            t_sec = k * DT

            pt = JointTrajectoryPoint()
            pt.time_from_start = Duration(
                sec=int(t_sec),
                nanosec=int(round((t_sec - int(t_sec)) * 1e9)),
            )

            for joint in ARM_JOINTS:
                noise_val = perlin_noise(
                    self._amplitude,
                    sample_time,
                    self._frequency,
                    SEED_OFFSETS[joint],
                )
                target = base[joint] + noise_val
                lo, hi = JOINT_LIMITS[joint]
                target = max(lo, min(hi, target))
                pt.positions.append(target)

            pt.velocities    = [0.0] * len(ARM_JOINTS)
            pt.accelerations = [0.0] * len(ARM_JOINTS)
            traj.points.append(pt)

        self._pub.publish(traj)
        self._noise_time += DT


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PerlinNoiseRollingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
