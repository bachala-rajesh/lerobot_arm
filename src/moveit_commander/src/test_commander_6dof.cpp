// Dev tool — publishes a fixed 6-joint command every 500ms to test the 6dof
// commander. 6dof variant of test_commander.cpp (which sends 5 values).
//
// joint_command order (chain order):
//   [0] shoulder_pan  [1] shoulder_lift  [2] elbow_flex
//   [3] wrist_flex    [4] wrist_yaw      [5] wrist_roll

#include <chrono>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"

using namespace std::chrono_literals;

class TestCommanderNode : public rclcpp::Node
{
public:
  TestCommanderNode()
  : Node("test_commander_6dof_node")
  {
    // Create publisher
    publisher_ = this->create_publisher<std_msgs::msg::Float64MultiArray>("joint_command", 10);

    // Create timer that calls the timer_callback function every 500ms
    timer_ = this->create_wall_timer(
      500ms, std::bind(&TestCommanderNode::timer_callback, this));

    RCLCPP_INFO(this->get_logger(), "Test Commander 6dof Node has been started");
  }

private:
  void timer_callback()
  {
    auto message = std_msgs::msg::Float64MultiArray();
    // elbow_flex bent 0.5 and wrist_yaw 0.3 so the extra 6dof joint moves too
    message.data = {0.0, 0.0, 0.5, 0.0, 0.3, 0.0};

    RCLCPP_INFO(this->get_logger(), "Publishing 6dof joint command");
    publisher_->publish(message);
  }

  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr publisher_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TestCommanderNode>());
  rclcpp::shutdown();
  return 0;
}
