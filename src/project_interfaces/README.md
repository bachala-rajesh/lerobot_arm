# project_interfaces

Custom ROS2 messages, services, and actions for the Lamp Emotions robot project.

## Messages

| File | Purpose |
|------|---------|
| `msg/Audio.msg` | Raw audio data with metadata |
| `msg/AudioData.msg` | Audio byte buffer |
| `msg/AudioInfo.msg` | Audio stream parameters (rate, channels, encoding) |
| `msg/AudioStamped.msg` | Audio message with ROS timestamp |
| `msg/PoseCommand.msg` | 6-DOF pose command for the arm (x, y, z, roll, pitch, yaw) |

## Services

| File | Purpose |
|------|---------|
| `srv/DetectObjects.srv` | VLM object detection — send a text prompt, get labels and bounding boxes |
| `srv/FindGraspPose.srv` | Grasp pose estimation — send object label or bboxes, get ranked grasp poses |
| `srv/MusicPlay.srv` | Play a music/audio file by name |

## Actions

| File | Purpose |
|------|---------|
| `action/TTS.action` | Text-to-speech — send text, streams audio back as feedback |
| `action/SegmentObject.action` | SAM2 segmentation — send bboxes, get mask; supports live tracking mode |
