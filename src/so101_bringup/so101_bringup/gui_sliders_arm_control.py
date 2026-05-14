#!/usr/bin/env python3
"""
Simple PyQt6 GUI with sliders for a 6-DOF robotic arm.

Joints:
- shoulder_pan
- shoulder_lift
- elbow_flex
- wrist_flex
- wrist_roll
- gripper

This version does NOT connect to ROS2.
It only shows the window and lets you move sliders.
"""

#TODO: modify the code to work in pyqt5

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QSlider,
    QLineEdit,
    QMainWindow,
)
import sys
import threading
from rclpy.executors import SingleThreadedExecutor



# ROS 2 imports
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class RosArmPositionsPublisher(Node):
    def __init__(self, joint_names: List[str], arm_name: str) -> None :
        super().__init__("arm_position_gui_node")
        self._joint_names: List[str] = joint_names
        self._pos_publisher = self.create_publisher(
            Float64MultiArray,
            f"/{arm_name}/joints_position_controller/commands",
            10
        )
        
        self._timer = self.create_timer(0.1, self._timer_callback)
        
        self._latest_values : Dict[str, float] = {name: 0.0 for name in joint_names}
        
    def update_values(self, joint_values: Dict[str, float]) -> None :
        self._latest_values = joint_values
        
        
    def _timer_callback(self) -> None :
        msg = Float64MultiArray()
        msg.data = [self._latest_values[name] for name in self._joint_names]
        self._pos_publisher.publish(msg)
        
    def shutdown(self) -> None :
        self.destroy_node()
        rclpy.shutdown()

class JointSliderWidget(QWidget):
    """
    Widget that contains a vertical slider, a label, and a numeric display
    for a single joint.
    """

    def __init__(
        self,
        joint_name: str,
        min_rad: float = -3.14,
        max_rad: float = 3.14,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.joint_name: str = joint_name
        self.min_rad: float = min_rad
        self.max_rad: float = max_rad

        # Layout for this joint (vertical)
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        # Label with joint name
        self.label = QLabel(joint_name)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # Slider (vertical)
        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setValue(500)  # center position
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        # Numeric display (read-only)
        self.value_display = QLineEdit("0.000")
        self.value_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_display.setReadOnly(True)
        layout.addWidget(self.value_display)

        self.setLayout(layout)

        # Initialize display with the corresponding radian value
        self._on_slider_changed(self.slider.value())

    def _on_slider_changed(self, slider_value: int) -> None:
        """
        Convert slider integer (0..1000) to radians in [min_rad, max_rad]
        and update the numeric display.
        """
        ratio: float = slider_value / 1000.0
        rad_value: float = self.min_rad + ratio * (self.max_rad - self.min_rad)
        self.value_display.setText(f"{rad_value:.3f}")

    def get_radians(self) -> float:
        """
        Return current joint value in radians.
        """
        slider_value: int = self.slider.value()
        ratio: float = slider_value / 1000.0
        return self.min_rad + ratio * (self.max_rad - self.min_rad)



class ArmSlidersWindow(QMainWindow):
    """
    Main window that holds all joint sliders for the robotic arm.
    """

    def __init__(self, 
                 joint_names: List[str],
                 ros_arm_position_publisher_node: Optional[RosArmPositionsPublisher] = None) -> None:
        super().__init__()

        self.joint_names: List[str] = joint_names
        self.joint_widgets: Dict[str, JointSliderWidget] = {}
        self.ros_publisher_node: Optional[RosArmPositionsPublisher] = ros_arm_position_publisher_node

        self.setWindowTitle("SO-101 Arm Joint Sliders (PyQt6)")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Grid for joint sliders
        sliders_layout = QGridLayout()

        for idx, name in enumerate(self.joint_names):
            joint_widget = JointSliderWidget(name)
            sliders_layout.addWidget(joint_widget, 0, idx)
            self.joint_widgets[name] = joint_widget

        main_layout.addLayout(sliders_layout)

        # Optional: show current joint values in a single line
        self.summary_line = QLineEdit()
        self.summary_line.setReadOnly(True)
        main_layout.addWidget(self.summary_line)

        # Initial summary
        self.update_values()

        # Connect all sliders to update the summary field
        for widget in self.joint_widgets.values():
            widget.slider.valueChanged.connect(self.update_values)
        # Set a reasonable default size
        self.resize(900, 400)

    def update_values(self) -> None:
        """
        Update the summary line with all current joint values in radians.
        """
        parts: List[str] = []
        joint_values: Dict[str, float] = {}
        for name in self.joint_names:
            rad_value = self.joint_widgets[name].get_radians()
            joint_values[name] = rad_value
            parts.append(f"{name}={rad_value:.3f}")
        
        self.summary_line.setText("  |  ".join(parts))
        
        # Publish to ROS2 if publisher node is provided
        if self.ros_publisher_node:
            self.ros_publisher_node.update_values(joint_values)
            
        
        
        

def main() -> None:
    choice = input("Choose 'press 1' for leader, or 'press 2' for follower: ")
    if choice == "1":
        arm_name = "leader"
    elif choice == "2":
        arm_name = "follower"
    else:
        print("Invalid choice. Please select '1' or '2'.")
        return
    
    rclpy.init()

    app = QApplication(sys.argv)

    joint_names: List[str] = [
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    ]
    
    ros_arm_position_publisher_node = RosArmPositionsPublisher(joint_names, arm_name)
    
    executor = SingleThreadedExecutor()
    executor.add_node(ros_arm_position_publisher_node)
    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()
    
    window = ArmSlidersWindow(joint_names, ros_arm_position_publisher_node=ros_arm_position_publisher_node)
    window.show()

    # ensure ros2 shuts down whent he Qt app exits
    app.aboutToQuit.connect(ros_arm_position_publisher_node.shutdown)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
