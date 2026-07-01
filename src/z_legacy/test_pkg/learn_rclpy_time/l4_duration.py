import rclpy
from rclpy.node import Node
from rclpy.clock import ClockType


class Lesson4(Node):
    def __init__(self):
        super().__init__("lesson3")



def main():
    rclpy.init()
    node = Lesson4()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
