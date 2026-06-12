#!/usr/bin/env python3

# =============================================================================
# SCRIPT WORKFLOW
# =============================================================================
# 1. Initialization:
#    - Starts a ROS2 node named 'capture_person_images'.
#    - Subscribes to the '/oak/rgb/image_raw' camera topic.
#    - Prompts the user in the terminal to enter a person's name.
#
# 2. Directory Setup:
#    - Finds the workspace using the 'ISAAC_ROS_WS' environment variable.
#    - Creates a dedicated folder for the entered person's name inside
#      'src/face_recognition/data/'.
#    - If the folder already exists, it counts the existing images to
#      continue numbering from where it left off.
#
# 3. Image Capture Loop:
#    - Displays a live feed from the camera in a window.
#    - Listens for key presses in the window.
#
# 4. User Interaction:
#    - Press 's': Selects and freezes the current frame, showing it in a
#      new "Selected frame" window.
#    - Press 'w': Saves the selected frame to the person's folder with a
#      sequential filename (e.g., 'person_name_001.jpg').

# =============================================================================


import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from pathlib import Path
import os
from datetime import datetime


class CapturePersonImages(Node):
    def __init__(self):
        super().__init__("capture_person_images")

        # image subscriber
        self.image_sub = self.create_subscription(Image, "/oak/rgb/image_raw", self.image_callback, 10)

        # cv bridge object
        self.cv_bridge = CvBridge()

        # window
        self.view_window = "Live Feed (Press 's' to select, 'w' to save)"
        self.clicked_frame_window = "Selected frame"

        self.count = 0
        self.selected_frame = None

        # get user dir
        self.save_dir_path = None
        self.get_user_dir()

        # logging
        self.get_logger().info("Node for capturing human images started...")

    def get_user_dir(self):
        env_var = os.environ.get("ISAAC_ROS_WS", "/workspaces/isaac_ros-dev")
        workspace_path = Path(env_var)
        data_dir_path = workspace_path / "src" / "face_recognition" / "data"

        # get user_name
        self.person_name = str(input("Enter the person's name: "))

        # create dir if the username dir does not exists
        self.save_dir_path = data_dir_path / self.person_name

        if self.save_dir_path.exists() and self.save_dir_path.is_dir():
            self.get_logger().info("folder exists")
            self.num_images = sum(1 for f in self.save_dir_path.iterdir() if f.is_file())
            self.get_logger().info(f"📦 Number of files in folder {self.save_dir_path}: {self.num_images}")
        else:
            self.save_dir_path.mkdir(parents=True, exist_ok=True)
            self.get_logger().info(f"folder does not exists.. created a folder named {self.save_dir_path}")

    def image_callback(self, msg):
        if msg is None:
            self.get_logger().warn("Image message not received")
            return
        try:
            # decode the image message
            frame = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

            # display the live frames
            cv2.imshow(self.view_window, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("s"):
                self.selected_frame = frame.copy()
                cv2.imshow(self.clicked_frame_window, self.selected_frame)
                self.get_logger().info("Frame selected! Press 'w' to save this frame.")
            elif key == ord("w"):
                if self.selected_frame is not None:
                    self.count += 1
                    # Get current time and format it as YYYYMMDD_HHMMSS
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # Create the filename
                    filename = f"{self.person_name}_{timestamp}.jpg"
                    save_img_path = self.save_dir_path / filename
                    # Save the image
                    cv2.imwrite(str(save_img_path), self.selected_frame)
                    print(f"Successfuly saved the selected image. Total images: {self.count}")
                    self.selected_frame = None

        except Exception as e:
            self.get_logger().warn(f"cound not process the frame... {e}")

    def close_all_windows(self):
        cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = CapturePersonImages()
    rclpy.spin(node)
    node.close_all_windows()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
