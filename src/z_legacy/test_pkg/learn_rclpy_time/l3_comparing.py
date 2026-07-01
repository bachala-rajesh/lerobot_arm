import rclpy
from rclpy.node import Node
from rclpy.clock import ClockType


class Lesson3(Node):
    def __init__(self):
        super().__init__("lesson3")

        t1= self.get_clock().now()
        
        t2 = rclpy.time.Time(nanoseconds = t1.nanoseconds + 500_000_000,
                             clock_type = t1.clock_type)
        
        
        diff = t2 - t1
        self.get_logger().info(f"type: {type(diff)}")
        self.get_logger().info(f"diff in nanoseconds: {diff.nanoseconds}")
        self.get_logger().info(f"diff in seconds: {diff.nanoseconds / 1e9:.3f}")
        
        self.get_logger().info(f" t1 clock type: {t1.clock_type}")
        self.get_logger().info(f" t2 clock type: {t2.clock_type}")
 

def main():
    rclpy.init()
    node = Lesson3()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
