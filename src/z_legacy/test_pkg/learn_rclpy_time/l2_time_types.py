import rclpy
from rclpy.node import Node
from rclpy.clock import ClockType


class Lesson2(Node):
    def __init__(self):
        super().__init__("lesson2")

        now = self.get_clock().now()
        self.get_logger().info(f"Current time: {now.nanoseconds}")
        self.get_logger().info(f"now: {now.nanoseconds / 1e9:.3f}")

        sys_clock = rclpy.clock.Clock(clock_type = ClockType.SYSTEM_TIME)
        sys_now = sys_clock.now()
        self.get_logger().info(f"System time: {sys_now.nanoseconds/1e9:.3f}")
        
        steady_clock = rclpy.clock.Clock(clock_type = ClockType.STEADY_TIME)
        steady_now = steady_clock.now()
        self.get_logger().info(f"Steady time: {steady_now.nanoseconds/1e9:.3f}")


def main():
    rclpy.init()
    node = Lesson2()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
