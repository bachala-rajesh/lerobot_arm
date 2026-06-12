
#include <rclcpp/rclcpp.hpp>

#include "audio_common/audio_capturer_node.hpp"


int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<audio_common::AudioCapturerNode>();
  node->work();
  rclcpp::shutdown();
  return 0;
}
