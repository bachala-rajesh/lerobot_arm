import rclpy
from rclpy.node import Node
from rclpy.clock import ClockType


class Lesson4(Node):
    def __init__(self):
        super().__init__("lesson3")

        d1 = rclpy.time.Duration(seconds = 5)
        self.get_logger().info(f"5 seconds duration nanoseconds: {d1.nanoseconds}")
        self.get_logger().info(f"5 seconds duration secs: {d1.nanoseconds / 1e9:.3f}")
 

def main():
    rclpy.init()
    node = Lesson4()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
