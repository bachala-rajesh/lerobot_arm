#!/usr/bin/env python3
"""SO101 teleop node: joystick-to-velocity for SO101 robot.

Subscribes to /joy, applies deadzone and control mapping, and publishes
TwistStamped velocity commands to cmd_vel. Uses a multi-threaded executor
so joy callback and timer callback run in parallel.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import TwistStamped
import math
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup


class SO101_SPEED:
    """Default and limit speeds for teleop linear and angular motion."""

    LINEAR_SPEED = 0.1
    ANGULAR_SPEED = 0.1
    MAX_LINEAR_SPEED = 0.3
    MAX_ANGULAR_SPEED = 0.3
    SPEED_SCALING = 3


class GAMEPAD_DEADZONE:
    """Deadzone thresholds and timing for gamepad axes, buttons, and restart hold."""

    JOYSTICK_DEADZONE = 0.2
    BUTTON_DEADZONE = 0.5
    RESTART_BUTTON_HOLD_TIME = 3.0  # seconds


class ACTIONS:
    """Action names used in the control map (must match parameter keys in the yaml file)."""

    LINEAR_X = "linear_x"
    LINEAR_Y = "linear_y"
    LINEAR_Z = "linear_z"
    ROLL = "roll"
    PITCH = "pitch"
    YAW = "yaw"
    SPEED_SCALE = "speed_scale"


class TeleopNode(Node):
    """ROS 2 node that maps joystick input to TwistStamped velocity commands."""

    def __init__(self):
        """Initialize the node, load parameters, and create subscriptions/timer."""
        super().__init__(
            "so101_teleop_node",
            allow_undeclared_parameters=True,
            automatically_declare_parameters_from_overrides=True,
        )

        # intialize joystick mapping parameters
        self.hw_axes = {}
        self.hw_buttons = {}
        self.cmd_map = {}

        # read parameters
        self.load_joystick_layout()
        self.load_control_map()

        # joystick data
        self.joy_msg_timestamp = None

        # callback groups
        self.joy_callback_group = MutuallyExclusiveCallbackGroup()
        self.timer_callback_group = MutuallyExclusiveCallbackGroup()

        # Topics
        self.joy_subscriber = self.create_subscription(
            Joy, "joy", self.joy_callback, 10, callback_group=self.joy_callback_group
        )
        self.vel_publisher = self.create_publisher(TwistStamped, "cmd_vel", 10)

        # timer
        self.timer_ = self.create_timer(0.1, self.timer_callback)

        # Logging
        self.get_logger().info("so101 Teleop node Ready")

    def load_joystick_layout(self):
        """Load joystick hardware layout from ROS parameters.

        Reads all parameters under the "joy_layout" prefix and populates
        self.hw_axes and self.hw_buttons with mappings from logical names
        (e.g. "left_stick_x") to hardware indices.
        """
        joy_params = self.get_parameters_by_prefix("joy_layout")

        for name, param_obj in joy_params.items():
            # split names
            split_name = name.split(".")
            if len(split_name) < 2:
                continue

            category = split_name[0]  # "axes" or "buttons"
            key = split_name[1]  # The name of the axis/button
            val = param_obj.value  # The ID number

            if category == "axes":
                self.hw_axes[key] = val
            elif category == "buttons":
                self.hw_buttons[key] = val

    def load_control_map(self):
        """Load control map from parameters and bind actions to hardware IDs.

        Reads parameters under "teleop_control_map" and builds self.cmd_map:
        each action (e.g. linear_x, speed_scale) is mapped to a category
        ("axes" or "buttons") and the corresponding hardware ID from the
        joystick layout. Values are filled in by joy_callback.
        """
        ctrl_params = self.get_parameters_by_prefix("teleop_control_map")

        for name, param_object in ctrl_params.items():
            # split names
            split_name = name.split(".")
            if len(split_name) < 2:
                continue

            category = split_name[0]  # "locomotion_control" or "scale_control"
            action_name = split_name[1]  # The name of the axis/button
            physical_name = param_object.value  # The ID number

            # Find the ID for this physical_name
            real_id = None
            if physical_name in self.hw_axes:
                real_id = self.hw_axes[physical_name]
                self.cmd_map[action_name] = {
                    "category": "axes",
                    "id": real_id,
                }
            elif physical_name in self.hw_buttons:
                real_id = self.hw_buttons[physical_name]
                self.cmd_map[action_name] = {
                    "category": "buttons",
                    "id": real_id,
                }

            # store the real id
            if real_id is not None:
                self.get_logger().info(
                    f"Mapped action '{action_name}' -> ID {real_id} ('{physical_name}')"
                )
            else:
                self.get_logger().warn(
                    f"Physical control '{physical_name}' not found in axes or buttons."
                )

    def joy_callback(self, msg):
        """Process incoming joystick messages and update command values.

        Applies deadzone to axes and buttons, then stores the resulting
        values in self.cmd_map[action_name]["value"] for each mapped action.
        Also updates self.joy_msg_timestamp from the message header.

        Args:
            msg: sensor_msgs/Joy message; may be None (treated as no data).
        """
        # get the action data
        if msg is None:
            self.get_logger().warn("No joystick data received.")
            self.joy_msg_timestamp = None
            return

        self.joy_msg_timestamp = msg.header.stamp

        for action_name, action_data in self.cmd_map.items():
            if action_data["category"] == "axes":
                action_value = msg.axes[action_data["id"]]
                if abs(action_value) < GAMEPAD_DEADZONE.JOYSTICK_DEADZONE:
                    action_value = 0.0
            elif action_data["category"] == "buttons":
                action_value = msg.buttons[action_data["id"]]
                if abs(action_value) < GAMEPAD_DEADZONE.BUTTON_DEADZONE:
                    action_value = 0.0
            else:
                self.get_logger().warn(
                    f"Invalid category for action {action_name}: {action_data['category']}"
                )
                continue

            self.cmd_map[action_name]["value"] = action_value

    def timer_callback(self):
        """Publish velocity command from current joystick state.

        Runs at a fixed interval (0.1 s). Reads values from self.cmd_map,
        applies speed scaling and limits, and publishes a TwistStamped
        on cmd_vel. If no joystick data has been received yet, publishes
        an empty twist and returns.
        """
        if self.joy_msg_timestamp is None:
            self.get_logger().warn("No joystick data received.")
            self.vel_publisher.publish(TwistStamped())
            return

        lin_speed = SO101_SPEED.LINEAR_SPEED
        ang_speed = SO101_SPEED.ANGULAR_SPEED
        # speed scale check
        if self.cmd_map[ACTIONS.SPEED_SCALE]["value"] != 0.0:
            lin_speed = lin_speed * SO101_SPEED.SPEED_SCALING
            ang_speed = ang_speed * SO101_SPEED.SPEED_SCALING

        # apply the speed limits
        lin_speed = min(
            max(lin_speed, -SO101_SPEED.MAX_LINEAR_SPEED), SO101_SPEED.MAX_LINEAR_SPEED
        )
        ang_speed = min(
            max(ang_speed, -SO101_SPEED.MAX_ANGULAR_SPEED),
            SO101_SPEED.MAX_ANGULAR_SPEED,
        )

        # create speed command
        vel_cmd = TwistStamped()
        vel_cmd.header.stamp = self.joy_msg_timestamp

        if self.cmd_map[ACTIONS.LINEAR_X]["value"] != 0.0:
            vel_cmd.twist.linear.x = math.copysign(
                lin_speed, self.cmd_map[ACTIONS.LINEAR_X]["value"]
            )

        if self.cmd_map[ACTIONS.LINEAR_Y]["value"] != 0.0:
            vel_cmd.twist.linear.y = math.copysign(
                lin_speed, self.cmd_map[ACTIONS.LINEAR_Y]["value"]
            )

        if self.cmd_map[ACTIONS.LINEAR_Z]["value"] != 0.0:
            vel_cmd.twist.linear.z = math.copysign(
                lin_speed, self.cmd_map[ACTIONS.LINEAR_Z]["value"]
            )

        if self.cmd_map[ACTIONS.ROLL]["value"] != 0.0:
            vel_cmd.twist.angular.x = math.copysign(
                ang_speed, self.cmd_map[ACTIONS.ROLL]["value"]
            )

        if self.cmd_map[ACTIONS.PITCH]["value"] != 0.0:
            vel_cmd.twist.angular.y = math.copysign(
                ang_speed, self.cmd_map[ACTIONS.PITCH]["value"]
            )

        if self.cmd_map[ACTIONS.YAW]["value"] != 0.0:
            vel_cmd.twist.angular.z = math.copysign(
                ang_speed, self.cmd_map[ACTIONS.YAW]["value"]
            )

        # publish velocity and high level command
        self.vel_publisher.publish(vel_cmd)


def main(args=None):
    """Create the teleop node and run it with a multi-threaded executor.

    """
    rclpy.init(args=args)
    so101_teleop_node = TeleopNode()

    executor = MultiThreadedExecutor()
    executor.add_node(so101_teleop_node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass

    so101_teleop_node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
