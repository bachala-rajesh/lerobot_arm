# 🧑‍💻 face_recognition

A real-time face recognition pipeline in ROS 2 using **YuNet** + **FaceNet**, designed for deployment on edge devices like Jetson Orin NX. Supports both new person registration and live face recognition.

---

## 📦 Overview

This package provides a complete face recognition system for robotic applications. It detects faces using the **YuNet** face detector, extracts embeddings using **FaceNet**, and performs real-time recognition by comparing them against a local face embedding database.

---

## 🧠 Core Pipeline

1. **Face Detection** → using `YuNet` (ONNX)
2. **Face Embeddings** → extracted via `FaceNet` (PyTorch)
3. **Database Matching** → using cosine similarity against stored embeddings

---

## 🧰 Features

- 🧍 Register new individuals from webcam input  
- 🧠 Convert captured face images to embeddings using FaceNet  
- 🗃️ Store embeddings in a local database  
- 🎥 Perform real-time face recognition using a live video feed  


---

## 🗃️ Key Scripts

### `capture_person_images.py`
- 📸 Captures face images from a webcam
- Press 's' to save a frame
- Prompts user for name and info. Creates a directory under data/ for that person
- Saves multiple face images for later embedding generation

### `images_to_face_embeddings.py`
- Loads images from data/
- uses Yunet to extract faces
- Uses FaceNet to generate face embeddings
- Saves each person’s embeddings inside processed_data/

### `detect_faces_live.py`
- Starts a live video stream
- Detects faces using YuNet (ONNX)
- Extracts embeddings using FaceNet
- Compares live embeddings with the stored ones using cosine similarity
- Displays matched names with bounding boxes on the video stream

---

## 🚀 Launch
