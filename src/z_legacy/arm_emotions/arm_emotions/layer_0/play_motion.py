#!/usr/bin/env python3
"""ROS 2 node that publishes a recorded JointTrajectory to the follower arm."""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Duration as DurationMsg
import numpy as np
from hdf5_play import HDF5Play
import threading
import questionary
import time

from utilities import (
    YAMLParser,
    list_episode_files,
    Groups,
    Metadata,
)


class PlayMotion(Node):
    """Node that publishes recorded JointTrajectory msgs to the follower arm."""

    def __init__(self, emotion: str, episode: int) -> None:
        super().__init__("play_motion")

        yaml_parser = YAMLParser()
        self.record_frequency_ = yaml_parser.load_record_frequency()

        # create instance of HDF5Play class — let exceptions propagate to main()
        self.hdf_file_management_ = HDF5Play(emotion, episode)
        self.hdf_file_management_.open_file()

        # load recorded data into memory
        self.arm_pos_ = self.hdf_file_management_.get_dataset(Groups.ARM_POS)
        self.gripper_pos_ = self.hdf_file_management_.get_dataset(Groups.GRIPPER_POS)
        self.timestamps_ = self.hdf_file_management_.get_dataset(Groups.TIMESTAMPS)

        # split the stored joint_names into arm-vs-gripper (the two follower controllers)
        joint_names_attr = self.hdf_file_management_.get_metadata(Metadata.JOINT_NAMES)
        self.joint_names_ = [
            n.decode() if isinstance(n, bytes) else str(n) for n in joint_names_attr
        ]
        gripper_idx = self.joint_names_.index("gripper")
        self.arm_joint_names_ = [
            n for i, n in enumerate(self.joint_names_) if i != gripper_idx
        ]
        self.gripper_joint_name_ = "gripper"

        # publishers — one per follower controller
        self.arm_pub_ = self.create_publisher(
            JointTrajectory,
            "/follower/arm_controller/joint_trajectory",
            10,
        )
        self.gripper_pub_ = self.create_publisher(
            JointTrajectory,
            "/follower/gripper_controller/joint_trajectory",
            10,
        )

        # latest joint positions — used by emergency_stop() to know where to hold
        self.last_arm_pos_ = None
        self.last_gripper_pos_ = None
        self.joint_state_sub_ = self.create_subscription(
            JointState, "/follower/joint_states", self.joint_state_cb, 10
        )

        self.get_logger().info(
            f"Play motion node started — {len(self.timestamps_)} frames loaded"
        )

    def joint_state_cb(self, msg: JointState) -> None:
        """Cache the latest follower joint positions for emergency_stop()."""
        try:
            self.last_arm_pos_ = [
                msg.position[msg.name.index(n)] for n in self.arm_joint_names_
            ]
            self.last_gripper_pos_ = msg.position[msg.name.index("gripper")]
        except ValueError:
            # joint not present in this message — just skip this update
            pass

    def build_arm_msg(self) -> JointTrajectory:
        """Pack the arm joint trajectory into a single JointTrajectory message."""
        msg = JointTrajectory()
        msg.joint_names = self.arm_joint_names_

        points = []
        for t in range(len(self.timestamps_)):
            point = JointTrajectoryPoint()
            point.positions = [float(x) for x in self.arm_pos_[t]]
            point.time_from_start = self._to_duration(float(self.timestamps_[t, 0]))
            points.append(point)
        msg.points = points
        return msg

    def build_gripper_msg(self) -> JointTrajectory:
        """Pack the gripper trajectory into a single JointTrajectory message."""
        msg = JointTrajectory()
        msg.joint_names = [self.gripper_joint_name_]

        points = []
        for t in range(len(self.timestamps_)):
            point = JointTrajectoryPoint()
            point.positions = [float(self.gripper_pos_[t, 0])]
            point.time_from_start = self._to_duration(float(self.timestamps_[t, 0]))
            points.append(point)
        msg.points = points
        return msg

    @staticmethod
    def _to_duration(t_s: float) -> DurationMsg:
        sec = int(t_s)
        nsec = int((t_s - sec) * 1e9)
        return DurationMsg(sec=sec, nanosec=nsec)

    def start_play(self) -> float:
        """Publish arm + gripper trajectories once; return duration in seconds."""
        self.arm_pub_.publish(self.build_arm_msg())
        self.gripper_pub_.publish(self.build_gripper_msg())
        if len(self.timestamps_) == 0:
            return 0.0
        return float(self.timestamps_[-1, 0])

    def emergency_stop(self) -> None:
        """Cancel the running trajectory by publishing a 200ms hold at the
        current joint positions. Both controllers replace whatever they
        were running with this short hold trajectory."""
        if self.last_arm_pos_ is None or self.last_gripper_pos_ is None:
            self.get_logger().warn("No joint state received yet — cannot stop cleanly")
            return

        hold_time = DurationMsg(sec=0, nanosec=200_000_000)  # 200ms

        arm_msg = JointTrajectory()
        arm_msg.joint_names = self.arm_joint_names_
        arm_pt = JointTrajectoryPoint()
        arm_pt.positions = list(self.last_arm_pos_)
        arm_pt.time_from_start = hold_time
        arm_msg.points = [arm_pt]
        self.arm_pub_.publish(arm_msg)

        grip_msg = JointTrajectory()
        grip_msg.joint_names = [self.gripper_joint_name_]
        grip_pt = JointTrajectoryPoint()
        grip_pt.positions = [float(self.last_gripper_pos_)]
        grip_pt.time_from_start = hold_time
        grip_msg.points = [grip_pt]
        self.gripper_pub_.publish(grip_msg)


def main(args: list[str] | None = None) -> None:
    """Entry point for the play_motion node."""
    rclpy.init(args=args)
    yaml_parser = YAMLParser()

    thread = None
    node = None
    try:
        emotions = yaml_parser.load_emotions_list()
        emotion = questionary.select("choose one emotion", choices=emotions).ask()
        if emotion is None:
            return

        # list available episodes for this emotion
        episode_files = list_episode_files(emotion)
        if not episode_files:
            questionary.print(
                f"No episodes found for emotion {emotion!r}", style="bold fg:red"
            )
            return

        episode_choices = [p.stem for p in episode_files]
        chosen = questionary.select("choose one episode", choices=episode_choices).ask()
        if chosen is None:
            return
        episode = int(chosen.split("_")[-1])

        # start the node — let HDF5Play exceptions propagate
        node = PlayMotion(emotion, episode)
        thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        thread.start()

        # give publishers time to discover their controllers
        time.sleep(2)

        confirm = questionary.confirm(
            "press Enter to continue to play the motion?"
        ).ask()
        if not confirm:
            return

        duration = node.start_play()
        questionary.print(
            f"Playing back {duration:.2f}s trajectory... (press any key to abort)",
            style="bold fg:yellow",
        )

        # The prompt does double duty: pressing during motion = abort;
        # pressing after motion ends = just continue to metadata edits.
        start = time.time()
        questionary.press_any_key_to_continue(
            "press any key to STOP the motion (or press after it finishes to continue)"
        ).ask()
        elapsed = time.time() - start

        if elapsed < duration:
            node.emergency_stop()
            questionary.print(f"Motion aborted at {elapsed:.2f}s", style="bold fg:red")
        else:
            questionary.print("Playback finished", style="bold fg:green")

        # ---- metadata edit loop ----
        # All edits are staged in local variables for crash safety.
        # Nothing is written to the file (or moved on disk) until the
        # commit block below — if the program dies before then, the file
        # stays exactly as it was loaded.
        staged_emotion = node.hdf_file_management_.emotion
        staged_user_comment = None  # None = "no change"
        staged_user_rating = None

        while True:
            answer = questionary.select(
                "Do you want to modify the metadata?",
                choices=[
                    Metadata.EMOTION.value,
                    Metadata.USER_COMMENT.value,
                    Metadata.USER_RATING.value,
                    "No",
                ],
            ).ask()

            if answer in ("No", None):
                break

            if answer == Metadata.EMOTION.value:
                questionary.print(
                    f"Current emotion: {staged_emotion}", style="bold fg:yellow"
                )
                new_emotion = questionary.select(
                    "choose new emotion", choices=emotions
                ).ask()
                if new_emotion is not None:
                    staged_emotion = new_emotion

            elif answer == Metadata.USER_COMMENT.value:
                current = node.hdf_file_management_.get_metadata(Metadata.USER_COMMENT)
                questionary.print(
                    f"Current user comment: {current}", style="bold fg:yellow"
                )
                new_comment = questionary.text(
                    "Please input the new user comment:", default=""
                ).ask()
                if new_comment is not None:
                    staged_user_comment = new_comment

            elif answer == Metadata.USER_RATING.value:
                current = node.hdf_file_management_.get_metadata(Metadata.USER_RATING)
                questionary.print(
                    f"Current user rating: {current}", style="bold fg:yellow"
                )
                new_rating = questionary.text(
                    "Please input the new user rating:", default=""
                ).ask()
                if new_rating is not None:
                    staged_user_rating = new_rating

        # ---- commit all staged changes in one shot ----
        if staged_user_comment is not None:
            node.hdf_file_management_.modify_metadata(
                Metadata.USER_COMMENT, staged_user_comment
            )
        if staged_user_rating is not None:
            node.hdf_file_management_.modify_metadata(
                Metadata.USER_RATING, staged_user_rating
            )
        # EMOTION last — close_file() reads the in-file attr to decide whether
        # to relocate. Writing it last keeps the inconsistency window minimal.
        if staged_emotion != node.hdf_file_management_.emotion:
            node.hdf_file_management_.modify_metadata(Metadata.EMOTION, staged_emotion)

        node.hdf_file_management_.close_file()
        questionary.print(
            f"Saved to: {node.hdf_file_management_.hdf5_file_path}",
            style="bold fg:yellow",
        )
    except KeyboardInterrupt:
        pass
    finally:
        # safety net: close the file if it's still open (e.g. on exception)
        if node is not None and node.hdf_file_management_.hdf5_file is not None:
            try:
                node.hdf_file_management_.close_file()
            except Exception:
                pass
        rclpy.shutdown()
        if thread is not None:
            thread.join()


if __name__ == "__main__":
    main()
