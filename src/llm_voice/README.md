# llm_voice

Voice assistant for the SO-101 robot using Pipecat + LangGraph + Qwen models via DashScope.

Pipeline: **Mic → STT → LangGraph agent (with ROS2 tools) → TTS → Speaker**

---

## Active scripts

| File | Purpose |
|------|---------|
| `v5_pipecat_langgraph.py` | **Current main** — full voice pipeline with `detect_objects` + `scene_db` tools |
| `v6_pipecat_langgraph.py` | v5 + debug prints to trace LangGraph node emissions |

### Earlier iterations (kept for reference)

| File | What was added |
|------|----------------|
| `v1_test_langchain.py` | LangGraph + real `/vlm/detect_objects` ROS2 service |
| `v2_test_langchain_scene_db.py` | + scene_db query tool |
| `v3_test_langchain_pipecat_scene_db_tools.py` | + Pipecat audio pipeline |
| `v4_test_langchain_pipecat.py` | Pipecat + LangGraph combined |

---

## Services (custom Pipecat integrations)

### STT (`services/stt/`)

| File | Model | Notes |
|------|-------|-------|
| `stt_qwen3_flash.py` | `qwen3-asr-flash` | Synchronous HTTP, returns emotion annotation |
| `stt_qwen_realtime.py` | `qwen-asr-realtime` | Streaming realtime variant |
| `stt_paraformer.py` | Paraformer | Offline alternative |

### TTS (`services/tts/`)

| File | Model | Notes |
|------|-------|-------|
| `tts_qwen3_flash.py` | `qwen3-tts-flash` | Non-streaming |
| `tts_qwen3_flash_realtime.py` | `qwen3-tts-flash-realtime` | Streaming v1 |
| `tts_qwen3_flash_realtime_v2.py` | `qwen3-tts-flash-realtime` | Streaming v2 (current) |

---

## Processors

| File | Purpose |
|------|---------|
| `processors/emotion_tag_processor.py` | Sits between LLM and TTS. Detects `[emotion]` tags in LLM stream, strips them, sends TTS voice-change instructions |

---

## Frames

| File | Purpose |
|------|---------|
| `frames/tts_instruction_update_frames.py` | Custom Pipecat `ControlFrame` subclass for sending voice-change instructions to the TTS service |

---

## Function calling tools (`function_calling/`)

| Tool | Purpose |
|------|---------|
| `capture_image` | Captures a camera frame |
| `describe_image` | Calls `/vlm/detect_objects` and returns description |
| `get_current_time` | Returns current time |
| `get_weather` | Fetches weather (stub or external API) |
| `recall` | Reads from robot memory |
| `remember` | Writes to robot memory |
| `search_news` | Searches news |

---

## API key required

```bash
export DASHSCOPE_API_KEY=your_key_here
```

All STT, TTS, and LLM calls go to `dashscope.aliyuncs.com`.

---

## Run

```bash
source install/setup.bash
python src/llm_voice/llm_voice/v5_pipecat_langgraph.py
```

MoveIt2 and `vlm_perception` node must be running for robot tools to work.
