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
from hdf_file_management import HDFFileManagement, MotionType
import threading
import questionary
import time



class RecordMotion(Node):
    """Node that prints incoming JointState messages."""

    def __init__(self, emotion: str) -> None:
        super().__init__("record_motion")
        
        self.parent_frame = "follower_base_link"
        self.child_frame = "follower_gripper_link"
        self.record_frequency = 50
        self.dt = 1.0 / self.record_frequency
        
        self.joint_pos_ = np.array([])
        self.joint_vel_ = np.array([])
        self.joint_msg_timestamp_ = None
        self.joint_names_ = np.array([])
        self.init_timestamp_ = None
        self.ee_pose_ = np.array([])
        
        
        self.subscription_ = self.create_subscription(
            JointState,
            "joint_states",
            self.joint_states_callback,
            10,
        )
        
        self.tf_buffer_ = tf2_ros.Buffer()
        self.tf_listener_ = tf2_ros.TransformListener(self.tf_buffer_, self)
        
        self.timer_ = self.create_timer(self.dt, self.timer_callback)
        
        # create instance of HDFFileManagement class
        self.hdf_file_management_ = HDFFileManagement(emotion)
        
        # latest_joint_state_status and latest_ee_pose_status
        self.latest_joint_state_status_ = False
        self.latest_ee_pose_status_ = False
        self.init_joint_msg_status_ = False
        self.init_tf_msg_status_ = False
        
        self.gripper_idx_ = None
        self.arm_idx_ = None
        
        
        self.get_logger().info("Record motion node started")
        

    def joint_states_callback(self, msg: JointState) -> None:
        if not self.init_joint_msg_status_:
            self.joint_names_ = np.array(msg.name)
            self.init_timestamp_ = self.get_clock().now()
            self.gripper_idx_ = self.joint_names_.index("gripper")
            self.arm_idx_ = [i for i in range(len(self.joint_names_)) if i != self.gripper_idx_]
            self.init_joint_msg_status_ = True
            
        self.joint_pos_ = np.array(msg.position)
        self.joint_vel_ = np.array(msg.velocity)
        self.joint_msg_timestamp_ = (self.get_clock().now() - self.init_timestamp_).nanoseconds * 1e-9  #seconds
        self.latest_joint_state_status_ = True
        
        
        
        
    def timer_callback(self):
        """Print the current EE pose."""
        
        self.get_ee_pose()
        if not self.latest_ee_pose_status_:
            return
        
        if not self.latest_joint_state_status_:
            return
        
        self.hdf_file_management_.append_frame(
                arm_pos = self.joint_pos_[self.arm_idx_],
                gripper_pos = self.joint_pos_[self.gripper_idx_],
                arm_vel = self.joint_vel_[self.arm_idx_],
                gripper_vel = self.joint_vel_[self.gripper_idx_],
                ee_pose = self.ee_pose_,
                joint_msg_timestamp = self.joint_msg_timestamp_
        )
        
        self.latest_joint_state_status_ = False
        self.latest_ee_pose_status_ = False
        
    def get_ee_pose(self):
        try:
            t = self.tf_buffer_.lookup_transform(
                self.parent_frame,
                self.child_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.05)
            )
            self.init_tf_msg_status_ = True
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
  
    try:
        emotions = HDFFileManagement.load_emotions_list()
        emotion = questionary.select(
            "choose one emotion", choices=emotions
        ).ask()
        
        node = RecordMotion(emotion)
    
        # start the node in different thread
        thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        thread.start()
        
        # wait for joint state to be available
        while True:
            if node.init_tf_msg_status_:
                break
            else:
                time.sleep(1)
        
        question = questionary.confirm("press Enter to continue to record the motion?")
        question.ask()
        
        node.hdf_file_management_.start_record()
        start_time = node.get_clock().now()
        
        question = questionary.confirm("Recording in progress...., press Enter to stop the recording?")
        question.ask()
        
        node.hdf_file_management_.stop_record()
        finish_time = node.get_clock().now()
        duration = (finish_time - start_time).nanoseconds * 1e-9  #seconds
            
        question = questionary.select("Do you want to save the recording?", choices=["Yes", "No"])
        answer = question.ask()
        
        if answer == "No":
            node.hdf_file_management_.close_file()
            node.hdf_file_management_.delete_file()
            questionary.print("Recording not saved", style='bold fg:red')
        elif answer == "Yes":
            # ask for metadata
            # question = questionary.text("Please input the metadata of the recording:")
            motion_basis = MotionType.TELEPORT.value
            user_comment = questionary.text("Please input the user comment of the recording:", 
                                            default="").ask()
            
            node.hdf_file_management_.add_metadata(
                motion_basis=motion_basis,
                duration=duration,
                user_comment=user_comment,
                joint_names=node.joint_names_.tolist(),
            )
            node.hdf_file_management_.close_file()
            questionary.print(f"Recorded the motion of duration {duration:.3f} seconds.. saved to {node.hdf_file_management_.hdf5_file_path}", style='bold fg:yellow')
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()
        thread.join()
    
    
if __name__ == "__main__":
    main()
