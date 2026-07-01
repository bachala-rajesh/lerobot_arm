#!/usr/bin/env python3
"""ROS 2 node that replays a LeLamp CSV recording on the SO-101 follower arm.

Reads CSVs downloaded from humancomputerlab/lelamp_runtime
(motion_recordings/test_downloaded/<name>.csv), remaps the lamp's 5 joint
columns onto the SO-101 arm joints, converts degrees to radians, and publishes
a single JointTrajectory to /follower/arm_controller/joint_trajectory. The
gripper is held at a fixed position via /follower/gripper_controller/joint_trajectory.

Usage:
    ros2 run arm_emotions play_lelamp_csv.py --name nod
    ros2 run arm_emotions play_lelamp_csv.py --name happy_wiggle --speed 0.5
"""

from __future__ import annotations

import argparse
import csv
import math
import threading
import time
from pathlib import Path

import rclpy
from builtin_interfaces.msg import Duration as DurationMsg
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


# LeLamp CSV column  ->  SO-101 joint name
LELAMP_TO_SO101 = {
    "base_yaw.pos": "shoulder_pan",
    "base_pitch.pos": "shoulder_lift",
    "elbow_pitch.pos": "elbow_flex",
    "wrist_pitch.pos": "wrist_flex",
    "wrist_roll.pos": "wrist_roll",
}

# SO-101 arm joint order expected by /follower/arm_controller
SO101_ARM_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]

GRIPPER_JOINT = "gripper"
GRIPPER_HOLD_RAD = 0.0  # neutral pose for the SO-101 gripper

RECORDINGS_DIR = Path(
    "/home/mira/workspaces/lerobot_ws/src/motion_recordings/test_downloaded"
)


def _to_duration(t_s: float) -> DurationMsg:
    sec = int(t_s)
    nsec = int((t_s - sec) * 1e9)
    return DurationMsg(sec=sec, nanosec=nsec)


def load_lelamp_csv(csv_path: Path) -> tuple[list[float], list[list[float]]]:
    """Read a LeLamp CSV. Returns (rel_times_seconds, arm_positions_rad[T][5]).

    - Timestamps are normalized so the first frame is at t = 0.
    - Joint values are converted degrees -> radians.
    - Columns are reordered to match SO101_ARM_JOINTS.
    """
    times: list[float] = []
    positions: list[list[float]] = []

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in LELAMP_TO_SO101 if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"CSV {csv_path.name} missing expected columns: {missing}. "
                f"Got: {reader.fieldnames}"
            )

        t0 = None
        for row in reader:
            t = float(row["timestamp"])
            if t0 is None:
                t0 = t
            times.append(t - t0)

            # build the row in SO-101 joint order
            so101_row = []
            for so101_name in SO101_ARM_JOINTS:
                # find the lamp column that maps to this so101 name
                lamp_col = next(
                    c for c, n in LELAMP_TO_SO101.items() if n == so101_name
                )
                so101_row.append(math.radians(float(row[lamp_col])))
            positions.append(so101_row)

    return times, positions


class PlayLeLampCSV(Node):
    def __init__(self, recording_name: str, speed: float) -> None:
        super().__init__("play_lelamp_csv")

        csv_path = RECORDINGS_DIR / f"{recording_name}.csv"
        if not csv_path.is_file():
            raise FileNotFoundError(f"Recording not found: {csv_path}")

        self.times_, self.arm_positions_ = load_lelamp_csv(csv_path)
        if speed <= 0:
            raise ValueError("--speed must be > 0")
        self.times_ = [t / speed for t in self.times_]

        self.arm_pub_ = self.create_publisher(
            JointTrajectory, "/follower/arm_controller/joint_trajectory", 10
        )
        self.gripper_pub_ = self.create_publisher(
            JointTrajectory, "/follower/gripper_controller/joint_trajectory", 10
        )

        # cache the latest follower joint state for emergency_stop()
        self.last_arm_pos_ = None
        self.last_gripper_pos_ = None
        self.create_subscription(
            JointState, "/follower/joint_states", self._joint_state_cb, 10
        )

        self.get_logger().info(
            f"Loaded {recording_name}.csv: {len(self.times_)} frames, "
            f"duration {self.times_[-1]:.2f}s (speed x{speed})"
        )

    def _joint_state_cb(self, msg: JointState) -> None:
        try:
            self.last_arm_pos_ = [
                msg.position[msg.name.index(n)] for n in SO101_ARM_JOINTS
            ]
            self.last_gripper_pos_ = msg.position[msg.name.index(GRIPPER_JOINT)]
        except ValueError:
            pass

    def _build_arm_msg(self) -> JointTrajectory:
        msg = JointTrajectory()
        msg.joint_names = SO101_ARM_JOINTS
        points = []
        for t, pos in zip(self.times_, self.arm_positions_):
            pt = JointTrajectoryPoint()
            pt.positions = [float(x) for x in pos]
            pt.time_from_start = _to_duration(t)
            points.append(pt)
        msg.points = points
        return msg

    def _build_gripper_msg(self) -> JointTrajectory:
        msg = JointTrajectory()
        msg.joint_names = [GRIPPER_JOINT]
        pt = JointTrajectoryPoint()
        pt.positions = [GRIPPER_HOLD_RAD]
        pt.time_from_start = _to_duration(self.times_[-1] if self.times_ else 0.0)
        msg.points = [pt]
        return msg

    def start_play(self) -> float:
        self.arm_pub_.publish(self._build_arm_msg())
        self.gripper_pub_.publish(self._build_gripper_msg())
        return float(self.times_[-1]) if self.times_ else 0.0

    def emergency_stop(self) -> None:
        if self.last_arm_pos_ is None or self.last_gripper_pos_ is None:
            self.get_logger().warn("No joint state received — cannot stop cleanly")
            return
        hold = DurationMsg(sec=0, nanosec=200_000_000)

        arm_msg = JointTrajectory()
        arm_msg.joint_names = SO101_ARM_JOINTS
        arm_pt = JointTrajectoryPoint()
        arm_pt.positions = list(self.last_arm_pos_)
        arm_pt.time_from_start = hold
        arm_msg.points = [arm_pt]
        self.arm_pub_.publish(arm_msg)

        grip_msg = JointTrajectory()
        grip_msg.joint_names = [GRIPPER_JOINT]
        grip_pt = JointTrajectoryPoint()
        grip_pt.positions = [float(self.last_gripper_pos_)]
        grip_pt.time_from_start = hold
        grip_msg.points = [grip_pt]
        self.gripper_pub_.publish(grip_msg)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        required=True,
        help="Recording name without .csv (e.g. nod, happy_wiggle, idle)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed multiplier (1.0 = original, 0.5 = half speed)",
    )
    args = parser.parse_args(argv)

    rclpy.init()
    node = None
    spin_thread = None
    try:
        node = PlayLeLampCSV(args.name, args.speed)
        spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        spin_thread.start()

        # let publishers discover the controllers + joint state come in
        time.sleep(2.0)

        input("Press Enter to play (Ctrl-C during motion = emergency stop)... ")
        duration = node.start_play()
        node.get_logger().info(f"Playing {duration:.2f}s...")
        time.sleep(duration + 0.5)
        node.get_logger().info("Done")

    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().warn("Interrupted — emergency stop")
            node.emergency_stop()
            time.sleep(0.3)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
        if spin_thread is not None:
            spin_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
