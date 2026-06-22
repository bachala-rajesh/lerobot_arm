# Research Preview — grasp-model
Date: 2026-06-18

Instructions:
Delete the "## Paper N" blocks you do NOT want to save.
Keep only the papers you want.
Then run: /agent-research grasp-model --save

---

## Paper 1: GraspSAM: When Segment Anything Model Meets Grasp Detection
**Type:** paper + repo
**Link:** https://arxiv.org/abs/2409.12521 | https://github.com/gist-ailab/GraspSAM
**Tags:** #grasp-model #sam #planar-grasp #bbox-prompt
**Also useful for:** segmentation-grasp-pipeline

What it proposes: Single model that takes SAM-style prompts (bbox, point, or text) and outputs both segmentation mask + planar grasp rectangle. Natively consumes SAM2 outputs.
Tools/libs used: PyTorch, SAM (Meta), segment-anything
Robot assumed: Generic tabletop arm. Not robot-specific.
ROS2 compatible: No native — pure Python inference, wrappable in ROS2 node
Offline capable: Yes — no cloud dependency
Compute needed: SAM-ViT-B fits in ~6 GB VRAM. Jetson Orin NX compatible.

---

## Paper 2: SAM2Grasp: Resolve Multi-modal Grasping via Prompt-conditioned Temporal Action Prediction
**Type:** paper
**Link:** https://arxiv.org/abs/2512.02609
**Tags:** #grasp-model #sam2 #6dof #trajectory #temporal
**Also useful for:** tracking-grasp

What it proposes: Built on frozen SAM2 backbone. Takes initial bbox prompt (from VLM), uses SAM2 temporal tracking to predict continuous 6DOF grasp trajectory without re-prompting every frame.
Tools/libs used: SAM2 (Meta), PyTorch
Robot assumed: Generic. Paper focused on pipeline architecture.
ROS2 compatible: No native — architecture suits ROS2 camera topic input
Offline capable: Yes
Compute needed: SAM2 frozen backbone + small action head. Inference-efficient. Specific VRAM TBD.

Note: Code not yet public (Dec 2024 paper). Watch GitHub for release.

---

## Paper 3: Contact-GraspNet: Efficient 6-DoF Grasp Generation in Cluttered Scenes
**Type:** repo
**Link:** https://github.com/NVlabs/contact_graspnet | PyTorch port: https://github.com/elchun/contact_graspnet_pytorch
**Tags:** #grasp-model #6dof #depth #segmap #nvlabs
**Also useful for:** cluttered-scene-grasp

What it proposes: Accepts depth map + optional segmentation map. Uses SAM2 segmap directly via --local_regions flag to crop 3D regions per object. Outputs full 6DOF grasp poses (SE3) with contact points.
Tools/libs used: TensorFlow (official) or PyTorch (community port), Open3D, NumPy
Robot assumed: Generic 6DOF gripper. ICCV 2021, widely used.
ROS2 compatible: ROS1 wrapper exists (contact_graspnet_ros). No official ROS2 — needs porting.
Offline capable: Yes
Compute needed: 8 GB VRAM minimum. Jetson Orin NX 16 GB unified — compatible.

---

## Paper 4: AnyGrasp: Robust and Efficient Grasp Perception in Spatial and Temporal Domains
**Type:** SDK (licensed)
**Link:** https://github.com/graspnet/anygrasp_sdk | https://arxiv.org/pdf/2212.08333
**Tags:** #grasp-model #6dof #rgb-d #licensed
**Also useful for:** dense-grasp

What it proposes: Dense 6DOF grasp pose prediction from RGB-D point cloud. Best-in-class quality. Optional mask input to filter outputs.
Tools/libs used: Custom compiled .so library (licensed), PyTorch, Open3D
Robot assumed: Generic gripper. IEEE T-RO 2023.
ROS2 compatible: No native. Python API only.
Offline capable: Yes — but requires license registration per machine (machine ID-based)
Compute needed: x86 + CUDA only. aarch64/ARM NOT supported yet. CANNOT deploy on Jetson today.

WARNING: Skip for Jetson. Use only on x86 dev laptop for testing.

---

## Paper 5: GR-ConvNet v2: A Real-Time Multi-Grasp Detection Network for Robotic Grasping
**Type:** paper + repo
**Link:** https://www.mdpi.com/1424-8220/22/16/6208 | https://github.com/Loahit5101/GR-ConvNet-grasping
**Tags:** #grasp-model #planar-grasp #real-time #lightweight #rgb-d
**Also useful for:** fast-grasp-inference

What it proposes: Lightweight CNN that takes a cropped 224x224 image (RGB, D, or RGB-D) and outputs quality/angle/width maps for planar antipodal grasps. Crop ROI using SAM2 bbox before feeding.
Tools/libs used: PyTorch, NumPy, OpenCV
Robot assumed: Generic tabletop. Tested on Cornell Grasping Dataset. Sensors 2022.
ROS2 compatible: Original ROS1. Community ports exist. gist-ailab/deep-grasping has ROS wrapper.
Offline capable: Yes
Compute needed: 20 ms inference on modest GPU. Very Jetson-friendly. ONNX/TensorRT conversion feasible.

---

## Paper 6: Towards Open-World Grasping with Large Vision-Language Models (OWG)
**Type:** paper + repo
**Link:** https://arxiv.org/abs/2406.18722 | https://github.com/gtziafas/OWG
**Tags:** #grasp-model #vlm #6dof #open-vocabulary #end-to-end
**Also useful for:** vlm-manipulation-pipeline

What it proposes: 3-stage pipeline: VLM identifies object → SAM/GroundedSAM segments → Contact-GraspNet generates 6DOF poses. Language instruction in, ranked 6DOF grasps out. Swap VLM with Qwen-VL and segmentation with SAM2.
Tools/libs used: VLM (any), SAM/Grounded-SAM, Contact-GraspNet, PyTorch
Robot assumed: 6DOF arm (CoRL 2024 real-world experiments). 50% zero-shot grasp success.
ROS2 compatible: No native. Python pipeline, wrappable.
Offline capable: Partial — original uses GPT-4V (replace with Qwen-VL for offline)
Compute needed: Depends on VLM + Contact-GraspNet. 8+ GB VRAM.

---

## Paper 7: MapleGrasp: Mask-guided Feature Pooling for Language-driven Efficient Robotic Grasping
**Type:** paper + repo (pending)
**Link:** https://arxiv.org/abs/2506.06535 | https://github.com/vineet2104/MapleGrasp
**Tags:** #grasp-model #mask-guided #language #planar-grasp #2025
**Also useful for:** language-conditioned-grasp

What it proposes: Takes mask (from SAM2) + language query → pools features from masked region → predicts planar grasp at pixel level. Architecture nearly identical to this project's pipeline.
Tools/libs used: CLIP, PyTorch, custom RefGraspNet dataset
Robot assumed: Tabletop manipulation (RefGraspNet benchmark). Jun 2025 paper.
ROS2 compatible: No native.
Offline capable: Yes — CLIP is local
Compute needed: CLIP backbone + lightweight decoder. Efficient. Jetson-suitable. Specific VRAM TBD.

Note: Code pending post-publication. Check GitHub.

---

## Paper 8: HiFi-CS: Towards Open Vocabulary Visual Grounding for Robotic Grasping Using Vision-Language Models
**Type:** paper + repo
**Link:** https://arxiv.org/abs/2409.10419 | https://github.com/vineet2104/hifics
**Tags:** #grasp-model #vlm #visual-grounding #open-vocabulary #rgb
**Also useful for:** language-conditioned-grasp

What it proposes: Frozen VLM backbone + lightweight FiLM decoder for referred-object grasping. Works with GroundedSAM — SAM2 masks serve as grounding input directly. 100x smaller than full VLM.
Tools/libs used: PyTorch, CLIP or similar frozen VLM, GroundedSAM (optional)
Robot assumed: Tabletop arm. Real-world experiments. 90.33% visual grounding accuracy.
ROS2 compatible: No native. Python.
Offline capable: Yes
Compute needed: Lightweight by design. Jetson-suitable.
