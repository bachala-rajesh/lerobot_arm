---
title: OBB + YOLO Tabletop Grasp (Classical Geometry Approach)
type: technique
tags: [grasp-methods, classical-ideas, geometry, top-down, obb, yolo]
date: 2026-06-19
link: https://github.com/EclipseaHime017/reBot-DevArm-Grasp
also_useful_for: [lamp-emotions, voice-agent-grasping]
---

# OBB + YOLO Tabletop Grasp

## Key idea
Use YOLO instance segmentation to detect object mask. Fit an Oriented Bounding Box (OBB)
to the mask. Short axis of OBB = gripper rotation angle. Depth quantile at the mask region
= grasp height Z. Hand-eye calibration maps camera frame → robot base frame. No learned
grasp model — pure geometry.

This is a classical idea: geometry-first, no GPU for grasp pose estimation.

## Tools and libraries
- YOLO (Ultralytics) — detection + segmentation (CPU-capable)
- OpenCV — OBB fitting on segmentation mask
- NumPy — depth quantile computation
- Hand-eye calibration: TSAI Eye-in-Hand method (classical)
- Camera: any RGB-D (Orbbec, RealSense, OAK-D)

## Hardware and compute assumed
CPU-only for grasp pose estimation. YOLO can run on CPU (slow) or GPU (fast).
OAK-D can run YOLO on-device (Myriad X VPU) — zero GPU host load.

## Robot assumed
B601 arm (Seeed Studio reBot). Custom Python SDK. 6-DOF.
Similar in concept to SO-101 5-DOF — top-down grasp is valid for both.

## ROS2 integration
No. Pure Python. Custom arm SDK (not ROS2).
To use in ROS2: wrap YOLO + OBB logic in a ROS2 node.
Depth from OAK-D ROS2 topic → numpy array → same pipeline.

## Offline capability
Yes. Fully local. No cloud APIs.

## What transfers to SO-101 arm + Jetson
- The OBB grasp estimation logic (utils/ordinary_grasp.py in their repo)
- The hand-eye calibration approach (ArUco + TSAI)
- YOLO on OAK-D VPU — already possible with DepthAI SDK
- Top-down grasp works for SO-101 for simple tabletop pick tasks

## Limitations
- Top-down only. Cannot grasp objects from side or at angle.
- Fails for flat objects (thin book, plate) — OBB orientation misleading.
- Fails for highly symmetric objects — ambiguous short axis.
- Not 6-DOF. For more complex scenes, need Contact GraspNet or VGN.
- No collision checking.
