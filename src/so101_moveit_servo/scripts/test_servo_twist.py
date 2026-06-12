#!/usr/bin/env python3
"""Smoke test for MoveIt Servo on the SO101 follower arm.

What it does:
  1. Waits for /follower/servo_node/start_servo and calls it (Servo is paused on startup).
  2. Streams a constant TwistStamped to /follower/servo_node/delta_twist_cmds at 50 Hz.
  3. Cycles through +X, -X, +Z, -Z, +yaw, -yaw — a few seconds each — so you can see
     the EE move in every commanded direction.
  4. Sends a zero twist for the final second to halt cleanly, then calls stop_servo.

Run:
  ros2 launch so101_moveit_servo so101_servo.launch.py        # in terminal 1
  ros2 run so101_moveit_servo test_servo_twist.py             # in terminal 2

If the arm doesn't move:
  - ros2 service list | grep servo_node              # confirms Servo is up
  - ros2 topic echo /follower/servo_node/status      # 0 = OK, non-zero = halted (see moveit_servo/StatusCode)
  - ros2 topic echo /follower/servo_arm_controller/commands   # confirms Servo is emitting joint commands
  - ros2 control list_controllers -c /follower/controller_manager   # servo_arm_controller must be "active"
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import TwistStamped
from std_srvs.srv import Trigger


# (label, twist_dict, duration_s). twist_dict keys: lx, ly, lz, ax, ay, az  (defaults 0).
TEST_SEQUENCE = [
    ('+X linear  (forward)', {'lx': +0.03}, 3.0),
    ('-X linear  (back)',    {'lx': -0.03}, 3.0),
    ('+Z linear  (up)',      {'lz': +0.03}, 3.0),
    ('-Z linear  (down)',    {'lz': -0.03}, 3.0),
    ('+Z angular (yaw)',     {'az': +0.30}, 3.0),
    ('-Z angular (yaw)',     {'az': -0.30}, 3.0),
    ('HALT',                 {},            1.0),
]

PUBLISH_HZ = 50
TWIST_TOPIC = '/follower/servo_node/delta_twist_cmds'
START_SRV = '/follower/servo_node/start_servo'
STOP_SRV = '/follower/servo_node/stop_servo'
PLANNING_FRAME = 'follower_base_link'


class ServoSmokeTest(Node):

    def __init__(self) -> None:
        super().__init__('servo_smoke_test')

        # Reliable QoS — the Servo node subscribes with default (reliable) QoS for commands.
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._pub = self.create_publisher(TwistStamped, TWIST_TOPIC, qos)

        self._start_cli = self.create_client(Trigger, START_SRV)
        self._stop_cli = self.create_client(Trigger, STOP_SRV)

        self._current_twist = TwistStamped()
        self._current_twist.header.frame_id = PLANNING_FRAME

        # Stream the current twist at PUBLISH_HZ. Servo halts if commands stop
        # arriving (incoming_command_timeout = 0.1 s in servo_config.yaml).
        self._pub_timer = self.create_timer(1.0 / PUBLISH_HZ, self._publish_current)

    # ---------------------------------------------------------------- helpers
    def _publish_current(self) -> None:
        self._current_twist.header.stamp = self.get_clock().now().to_msg()
        self._pub.publish(self._current_twist)

    def _set_twist(self, t: dict) -> None:
        self._current_twist.twist.linear.x = float(t.get('lx', 0.0))
        self._current_twist.twist.linear.y = float(t.get('ly', 0.0))
        self._current_twist.twist.linear.z = float(t.get('lz', 0.0))
        self._current_twist.twist.angular.x = float(t.get('ax', 0.0))
        self._current_twist.twist.angular.y = float(t.get('ay', 0.0))
        self._current_twist.twist.angular.z = float(t.get('az', 0.0))

    def _call_trigger(self, client, name: str) -> bool:
        if not client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error(f'Service {name} not available — is so101_servo.launch.py running?')
            return False
        future = client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if future.result() is None:
            self.get_logger().error(f'Service {name} did not respond within 5 s')
            return False
        self.get_logger().info(f'{name} -> success={future.result().success} msg="{future.result().message}"')
        return future.result().success

    # --------------------------------------------------------------- sequence
    def run_sequence(self) -> None:
        if not self._call_trigger(self._start_cli, START_SRV):
            return

        for label, twist, duration in TEST_SEQUENCE:
            self.get_logger().info(f'>>> {label}  for {duration:.1f}s')
            self._set_twist(twist)

            end_time = self.get_clock().now().nanoseconds + int(duration * 1e9)
            while rclpy.ok() and self.get_clock().now().nanoseconds < end_time:
                rclpy.spin_once(self, timeout_sec=0.02)

        self._set_twist({})  # final safety zero
        self._call_trigger(self._stop_cli, STOP_SRV)
        self.get_logger().info('Done.')


def main() -> None:
    rclpy.init()
    node = ServoSmokeTest()
    try:
        node.run_sequence()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
