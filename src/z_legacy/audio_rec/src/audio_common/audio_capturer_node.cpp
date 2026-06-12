

#include <memory>
#include <portaudio.h>
#include <rclcpp/rclcpp.hpp>

#include "audio_common/audio_capturer_node.hpp"
#include "so101_interfaces/msg/audio_stamped.hpp"

using namespace audio_common;

AudioCapturerNode::AudioCapturerNode() : Node("audio_capturer_node") {

  this->format_ = 1; // PCM format code for int16

  // Declare parameters with default values
  this->declare_parameter<int>("channels", 1);
  this->declare_parameter<int>("rate", 16000);
  this->declare_parameter<int>("chunk", 512);
  this->declare_parameter<int>("device", -1);
  this->declare_parameter<std::string>("frame_id", "");

  // Get parameters
  this->channels_ = this->get_parameter("channels").as_int();
  this->rate_ = this->get_parameter("rate").as_int();
  this->chunk_ = this->get_parameter("chunk").as_int();
  int device = this->get_parameter("device").as_int();
  this->frame_id_ = this->get_parameter("frame_id").as_string();

  // Initialize PortAudio
  PaError err = Pa_Initialize();
  if (err != paNoError) {
    RCLCPP_ERROR(this->get_logger(), "PortAudio error: %s",
                 Pa_GetErrorText(err));
    throw std::runtime_error("Failed to initialize PortAudio");
  }

  PaStreamParameters inputParameters;
  inputParameters.device = (device >= 0) ? device : Pa_GetDefaultInputDevice();
  inputParameters.channelCount = this->channels_;
  inputParameters.sampleFormat = paInt16; // Use 16-bit integer format
  inputParameters.suggestedLatency =
      Pa_GetDeviceInfo(inputParameters.device)->defaultLowInputLatency;
  inputParameters.hostApiSpecificStreamInfo = nullptr;

  err = Pa_OpenStream(&this->stream_, &inputParameters,
                      nullptr, // output parameters (not used)
                      this->rate_, this->chunk_, paClipOff, nullptr, nullptr);

  if (err != paNoError) {
    RCLCPP_ERROR(this->get_logger(), "Failed to open audio stream: %s",
                 Pa_GetErrorText(err));
    throw std::runtime_error("Failed to open PortAudio stream");
  }

  err = Pa_StartStream(this->stream_);
  if (err != paNoError) {
    RCLCPP_ERROR(this->get_logger(), "Failed to start audio stream: %s",
                 Pa_GetErrorText(err));
    throw std::runtime_error("Failed to start PortAudio stream");
  }

  this->audio_pub_ =
      this->create_publisher<so101_interfaces::msg::AudioStamped>(
          "audio", rclcpp::SensorDataQoS());

  RCLCPP_INFO(this->get_logger(), "AudioCapturer node started");
}

AudioCapturerNode::~AudioCapturerNode() {
  Pa_StopStream(this->stream_);
  Pa_CloseStream(this->stream_);
  Pa_Terminate();
}

void AudioCapturerNode::work() {
  while (rclcpp::ok()) {

    auto msg = so101_interfaces::msg::AudioStamped();
    msg.header.frame_id = this->frame_id_;
    msg.header.stamp = this->get_clock()->now();


    msg.audio.audio_data.data = this->read_data();


    msg.audio.info.format = this->format_;
    msg.audio.info.channels = this->channels_;
    msg.audio.info.chunk = this->chunk_;
    msg.audio.info.rate = this->rate_;

    this->audio_pub_->publish(msg);
  }
}

std::vector<int16_t> AudioCapturerNode::read_data() {
  std::vector<int16_t> data(this->chunk_ * this->channels_);
  Pa_ReadStream(this->stream_, data.data(), this->chunk_);
  return data;
}

