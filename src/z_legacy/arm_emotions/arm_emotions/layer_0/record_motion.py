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
from hdf5_record import HDF5Record
import threading
import questionary
import time

from utilities import (
    YAMLParser,
    MotionType,
)


class RecordMotion(Node):
    """Node that prints incoming JointState messages."""

    def __init__(self, emotion: str) -> None:
        super().__init__("record_motion")

        yaml_parser = YAMLParser()
        self.parent_frame_, self.child_frame_ = yaml_parser.load_parent_child_frame()
        self.record_frequency_ = yaml_parser.load_record_frequency()

        # create instance of HDF5Record class — let exceptions propagate to main()
        self.hdf_file_management_ = HDF5Record(
            emotion, motion_type=MotionType.TELEPORT
        )

        # general variables
        self.joint_names_ = None
        self.init_timestamp_ = None
        self.gripper_idx_ = None
        self.arm_idx_ = None
        self.joint_pos_ = None
        self.joint_vel_ = None
        self.joint_timestamp_ = None
        self.ee_pose_ = None

        # status variables
        self.latest_joint_state_status_ = False
        self.latest_ee_pose_status_ = False
        self.init_joint_msg_status_ = False
        
        self.subscriber_ = self.create_subscription(
            JointState, "/leader/joint_states", self.joint_states_callback, 10
        )

        self.timer_ = self.create_timer(1 / self.record_frequency_, self.timer_callback)
        self.tf_buffer_ = tf2_ros.Buffer()
        self.tf_listener_ = tf2_ros.TransformListener(self.tf_buffer_, self)

        self.get_logger().info("Record motion node started")

    def joint_states_callback(self, msg: JointState) -> None:
        if not self.init_joint_msg_status_:
            self.joint_names_ = msg.name
            self.init_timestamp_ = self.get_clock().now()
            self.gripper_idx_ = self.joint_names_.index("gripper")
            self.arm_idx_ = [
                i for i in range(len(self.joint_names_)) if i != self.gripper_idx_
            ]
            self.init_joint_msg_status_ = True

        self.joint_pos_ = np.array(msg.position)
        self.joint_vel_ = np.array(msg.velocity)
        self.joint_timestamp_ = (
            self.get_clock().now() - self.init_timestamp_
        ).nanoseconds * 1e-9  # seconds
        self.latest_joint_state_status_ = True

    def timer_callback(self):
        """Print the current EE pose."""

        self.get_ee_pose()
        if not self.latest_ee_pose_status_:
            return

        if not self.latest_joint_state_status_:
            return

        self.hdf_file_management_.append_frame(
            timestamp=self.joint_timestamp_,
            pose=self.ee_pose_,
            gripper_pos=self.joint_pos_[self.gripper_idx_],
            arm_pos=self.joint_pos_[self.arm_idx_],
            arm_vel=self.joint_vel_[self.arm_idx_],
            gripper_vel=self.joint_vel_[self.gripper_idx_],
        )

        self.latest_joint_state_status_ = False
        self.latest_ee_pose_status_ = False

    def get_ee_pose(self):
        try:
            t = self.tf_buffer_.lookup_transform(
                self.parent_frame_,
                self.child_frame_,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.05),
            )
        except TransformException as e:
            self.get_logger().error(f"TF lookup failed: {e}", throttle_duration_sec=2.0)
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

        self.ee_pose_ = np.array([x, y, z, qx, qy, qz, qw])
        self.latest_ee_pose_status_ = True


def main(args: list[str] | None = None) -> None:
    """Entry point for the joint_state_printer node."""
    rclpy.init(args=args)
    yaml_parser = YAMLParser()

    thread = None
    try:
        emotions = yaml_parser.load_emotions_list()
        emotion = questionary.select("choose one emotion", choices=emotions).ask()
        if emotion is None:
            return

        # start the node in different thread
        node = RecordMotion(emotion)
        thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        thread.start()

        # wait for joint state to be available... sleep for few seconds
        time.sleep(2)

        confirm = questionary.confirm(
            "press Enter to continue to record the motion?"
        ).ask()
        if not confirm:
            return  # no file created yet — nothing to clean

        node.hdf_file_management_.start_record()
        start_time = node.get_clock().now()

        confirm = questionary.confirm(
            "Recording in progress...., press Enter to stop the recording!"
        ).ask()
        node.hdf_file_management_.stop_record()
        finish_time = node.get_clock().now()
        duration = (finish_time - start_time).nanoseconds * 1e-9  # seconds

        if not confirm:
            # user escaped during stop prompt — discard the file
            node.hdf_file_management_.close_file()
            node.hdf_file_management_.delete_file()
            questionary.print("Recording discarded", style="bold fg:red")
            return

        answer = questionary.select(
            "Do you want to save the recording?", choices=["Yes", "No"]
        ).ask()

        if answer in ("No", None):
            node.hdf_file_management_.close_file()
            node.hdf_file_management_.delete_file()
            questionary.print("Recording not saved", style="bold fg:red")
        elif answer == "Yes":
            # ask for metadata
            # question = questionary.text("Please input the metadata of the recording:")
            motion_basis = MotionType.TELEPORT.value
            user_comment = questionary.text(
                "Please input the user comment of the recording:", default=""
            ).ask()

            node.hdf_file_management_.add_metadata(
                motion_basis=motion_basis,
                duration=duration,
                user_comment=user_comment,
                joint_names=node.joint_names_,
            )
            node.hdf_file_management_.close_file()
            questionary.print(
                f"Recorded the motion of duration {duration:.3f} seconds.. saved to {node.hdf_file_management_.hdf5_file_path}",
                style="bold fg:yellow",
            )
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()
        if thread is not None:
            thread.join()


if __name__ == "__main__":
    main()
