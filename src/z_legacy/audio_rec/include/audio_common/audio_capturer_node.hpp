
#ifndef AUDIO_COMMON__AUDIO_CAPTURER_NODE
#define AUDIO_COMMON__AUDIO_CAPTURER_NODE

#include <memory>
#include <portaudio.h>
#include <rclcpp/rclcpp.hpp>

#include "so101_interfaces/msg/audio_stamped.hpp"

namespace audio_common {

class AudioCapturerNode : public rclcpp::Node {
public:
  AudioCapturerNode();
  ~AudioCapturerNode() override;

  void work();

private:
  PaStream *stream_;
  int format_;
  int channels_;
  int rate_;
  int chunk_;
  std::string frame_id_;

  rclcpp::Publisher<so101_interfaces::msg::AudioStamped>::SharedPtr audio_pub_;

  // Methods
  std::vector<int16_t> read_data();
};

} // namespace audio_common

#endif