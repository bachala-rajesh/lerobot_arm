The mental model: 5 layers

  Everything you're building fits into one stack. Build bottom-up:

  ┌─────────────────────────────────────────────────┐
  │ 5. Behavior layer    "what should the arm do?"  │  → triggers DMPs from Lamp Emotions
  ├─────────────────────────────────────────────────┤
  │ 4. World model       "what is currently true?"  │  → /world/people, /world/objects,
  /world/gestures
  ├─────────────────────────────────────────────────┤
  │ 3. Perception nodes  "extract meaning"          │  → YOLO, MediaPipe, FER, VLM
  ├─────────────────────────────────────────────────┤
  │ 2. Camera + TF       "pixels with geometry"     │  → drivers, calibration, depth
  deprojection
  ├─────────────────────────────────────────────────┤
  │ 1. Hardware          "the cameras"              │  → external RGB-D + wrist RGB
  └─────────────────────────────────────────────────┘

  The mistake almost everyone makes is jumping to layer 3 before layer 2 is solid. You will
   lose weeks if the camera-to-robot calibration is wrong. Do the boring stuff first.

  ---
  Phase 0 — Foundations (do this once, properly)

  These are prerequisites for every HRI scenario. Don't skip.

  ┌──────────────────────────────────────┬─────────────────────────────────────────────┐
  │                 Task                 │               Why it matters                │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Pick & install the external RGB-D    │ Without standardized ROS topics you can't   │
  │ driver (realsense2_camera /          │ do anything else                            │
  │ depthai-ros / azure_kinect_ros)      │                                             │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Install wrist camera driver (USB UVC │ Same                                        │
  │  node or v4l2_camera)                │                                             │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Intrinsic calibration of both        │ Without this, your 2D→3D math is wrong by   │
  │ cameras (camera_calibration package) │ cm                                          │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │                                      │ This is the hard one. Use ArUco markers or  │
  │ Extrinsic calibration of external    │ hand-eye calibration (easy_handeye2).       │
  │ camera → robot base_link             │ Without it, "person at (x,y,z)" means       │
  │                                      │ nothing to the arm                          │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Hand-eye calibration of wrist camera │ Required only when you want the arm to act  │
  │  → wrist_link                        │ on what the wrist camera sees               │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │ TF tree: every camera publishes a    │ RViz lets you sanity-check this visually    │
  │ frame, all connected to base_link    │                                             │
  ├──────────────────────────────────────┼─────────────────────────────────────────────┤
  │                                      │ All your future perception nodes will       │
  │ One reusable "perception node        │ follow the same pattern: subscribe to       │
  │ template" pattern                    │ image+depth, run model, publish typed       │
  │                                      │ message                                     │
  └──────────────────────────────────────┴─────────────────────────────────────────────┘

  **Done = ** you can stand in front of the external camera, RViz shows the point cloud,
  and a known point in the cloud has the right (x, y, z) in base_link coordinates.

  ---
  Phase 1 — Person awareness (the foundation for all HRI)

  Goal: arm knows where any human is in its workspace.

  ┌───────────────────────┬────────────────────────────────────────────────────────────┐
  │       Component       │                        Tool / model                        │
  ├───────────────────────┼────────────────────────────────────────────────────────────┤
  │ Person detection (2D  │ YOLOv8 (person class) or MediaPipe Pose                    │
  │ bbox)                 │                                                            │
  ├───────────────────────┼────────────────────────────────────────────────────────────┤
  │ 2D→3D localization    │ Sample depth at bbox center → deproject with camera        │
  │                       │ intrinsics → transform to base_link                        │
  ├───────────────────────┼────────────────────────────────────────────────────────────┤
  │ Tracker (ID           │ ByteTrack or simple IoU+Kalman; or just nearest-neighbor   │
  │ persistence across    │ for one person                                             │
  │ frames)               │                                                            │
  ├───────────────────────┼────────────────────────────────────────────────────────────┤
  │                       │ Custom msg PersonDetection { id, position                  │
  │ ROS output            │ (geometry_msgs/Point), confidence } published on           │
  │                       │ /perception/people                                         │
  ├───────────────────────┼────────────────────────────────────────────────────────────┤
  │                       │ "Look-at-person" — compute joint angles so wrist camera    │
  │ Behavior demo         │ points at the published Point. Pure inverse kinematics, no │
  │                       │  DMP yet                                                   │
  └───────────────────────┴────────────────────────────────────────────────────────────┘

  **Done = ** the arm visually tracks you as you walk around in front of it.

  ---
  Phase 2 — Face + emotion + gaze
  
  Builds on Phase 1 — restrict face search to inside the person bbox to save compute.

  ┌─────────────────────┬──────────────────────────────────────────────────────────────┐
  │      Component      │                         Tool / model                         │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Face detection +    │ MediaPipe Face Mesh (468 landmarks) or RetinaFace            │
  │ landmarks           │                                                              │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Head pose           │ Derive from face landmarks via solvePnP, or use MediaPipe's  │
  │ (yaw/pitch/roll)    │ built-in                                                     │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Gaze direction      │ MediaPipe iris landmarks, or a model like L2CS-Net for       │
  │                     │ higher quality                                               │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Emotion             │ A FER (Facial Expression Recognition) model — fer Python     │
  │ classification      │ package, or HSEmotion, or DeepFace                           │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Eye contact         │ Combine head pose + gaze + person's 3D position relative to  │
  │ detection           │ robot's "eye" (wrist camera or sensor head)                  │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │ ROS output          │ Face { person_id, head_pose, gaze_vector, emotion,           │
  │                     │ eye_contact_bool } on /perception/faces                      │
  ├─────────────────────┼──────────────────────────────────────────────────────────────┤
  │                     │ "Make eye contact" (arm orients to maintain gaze alignment); │
  │ Behavior demos      │  "React to emotion" (curious DMP on smile, shy DMP on direct │
  │                     │  stare)                                                      │
  └─────────────────────┴──────────────────────────────────────────────────────────────┘

  **Done = ** the arm gets shy when you stare at it, perks up when you smile.

  ---
  Phase 3 — Gesture recognition

  ┌──────────────────┬─────────────────────────────────────────────────────────────────┐
  │    Component     │                          Tool / model                           │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Body pose        │ MediaPipe Pose (33 keypoints, CPU-friendly) or YOLOv8-pose      │
  │ keypoints        │                                                                 │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Hand landmarks   │ MediaPipe Hands (21 landmarks per hand)                         │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Simple gestures  │ Wave = wrist x-position oscillates; Point = arm extended,       │
  │ (rule-based)     │ finger direction vector; Thumbs-up = thumb landmark above other │
  │                  │  finger tips; Open palm = finger spread metric                  │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Complex gestures │ Stack pose features over a sliding window, classify with a      │
  │  (temporal)      │ small LSTM or 1D CNN. For your stage, rules are enough — don't  │
  │                  │ train models yet                                                │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ ROS output       │ Gesture { person_id, type, direction_vector?, confidence } on   │
  │                  │ /perception/gestures                                            │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Behavior demo    │ Wave at the arm → arm waves back (excited DMP); point at a      │
  │                  │ location → arm looks there                                      │
  └──────────────────┴─────────────────────────────────────────────────────────────────┘

  **Done = ** four reliable gestures (wave, point, thumbs-up, open palm) each trigger a
  different arm response.

  ---
  Phase 4 — Object awareness + hand-over

  This is where the wrist camera earns its keep.

  ┌──────────────────┬─────────────────────────────────────────────────────────────────┐
  │    Component     │                          Tool / model                           │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Object detection │ YOLOv8 (COCO classes covers cups, bottles, phones, books). For  │
  │                  │ custom objects later: fine-tune YOLO on a small dataset         │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Object 3D        │ Same deprojection trick as Phase 1, but from the external depth │
  │ position         │  camera                                                         │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Object 6-DoF     │                                                                 │
  │ pose (optional,  │ FoundationPose or MegaPose — heavy, defer unless needed         │
  │ harder)          │                                                                 │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │                  │ (1) detect human hand 3D position via MediaPipe + depth, (2)    │
  │ Hand-over        │ detect object in human's hand, (3) move arm to approach pose,   │
  │ coordination     │ (4) wrist camera takes over for fine alignment via visual       │
  │                  │ servoing, (5) close gripper when contact / force threshold      │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ ROS output       │ Object { class, position, dimensions?, in_hand_of_person_id? }  │
  │                  │ on /perception/objects                                          │
  ├──────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Behavior demo    │ Person holds cup out → arm approaches and "accepts" it          │
  └──────────────────┴─────────────────────────────────────────────────────────────────┘

  **Done = ** a clean hand-over with a cup.

  ---
  Phase 5 — High-level reasoning (VLM)

  You already have visual_language_reasoning/ in this repo. This phase wires it into the
  perception stack.

  ┌────────────────┬───────────────────────────────────────────────────────────────────┐
  │   Component    │                           Tool / model                            │
  ├────────────────┼───────────────────────────────────────────────────────────────────┤
  │ Frame capture  │ On-demand (button, voice command, idle interval) — VLMs are too   │
  │ trigger        │ slow to run continuously                                          │
  ├────────────────┼───────────────────────────────────────────────────────────────────┤
  │ VLM choice     │ Qwen-VL-7B locally (if you have GPU) or GPT-4V / Claude via API   │
  │                │ for quality. Your repo already has scaffolding for both           │
  ├────────────────┼───────────────────────────────────────────────────────────────────┤
  │                │ Structured output: "Describe what's happening. Output JSON:       │
  │ Prompt design  │ {people_count, primary_action, objects_visible,                   │
  │                │ suggested_response}"                                              │
  ├────────────────┼───────────────────────────────────────────────────────────────────┤
  │ Speech input   │ Whisper for STT → VLM gets the question grounded in the current   │
  │ (optional)     │ image                                                             │
  ├────────────────┼───────────────────────────────────────────────────────────────────┤
  │ ROS output     │ /perception/scene_description (String, ~1 Hz max)                 │
  ├────────────────┼───────────────────────────────────────────────────────────────────┤
  │ Behavior demo  │ "Hey arm, what am I holding?" → arm tilts head, VLM answers, arm  │
  │                │ gestures toward it                                                │
  └────────────────┴───────────────────────────────────────────────────────────────────┘

  **Done = ** the arm can answer open-ended questions about what it sees.

  ---
  Phase 6 — Integration: world model + behavior
  
  This is where it all becomes one robot, not five demos.

  ┌───────────────┬────────────────────────────────────────────────────────────────────┐
  │   Component   │                            What it does                            │
  ├───────────────┼────────────────────────────────────────────────────────────────────┤
  │               │ Subscribes to all /perception/* topics, maintains a current        │
  │ World model   │ snapshot: people[], faces[], gestures[], objects[], scene_summary. │
  │ node          │  Publishes /world/state at fixed rate. Handles staleness (drop     │
  │               │ entries not seen for N seconds).                                   │
  ├───────────────┼────────────────────────────────────────────────────────────────────┤
  │               │ A behavior tree (py_trees_ros) or simple state machine. Reads      │
  │ Behavior      │ /world/state, decides which DMP from Lamp Emotions to trigger.     │
  │ layer         │ E.g., "no person seen for 30s → idle DMP", "new person enters →    │
  │               │ curious DMP", "wave detected → excited DMP"                        │
  ├───────────────┼────────────────────────────────────────────────────────────────────┤
  │ DMP execution │ Your existing Layer 1 work plays the chosen DMP through the        │
  │               │ trajectory controller                                              │
  ├───────────────┼────────────────────────────────────────────────────────────────────┤
  │ Priority /    │ What if person waves while another is handing over a cup? Behavior │
  │ arbitration   │  tree handles priority                                             │
  └───────────────┴────────────────────────────────────────────────────────────────────┘

  **Done = ** the arm behaves coherently in an open-ended room with people.

  ---
  Cross-cutting things to keep in mind
  
  - Coordinate frames — every 3D quantity must be in base_link before the motion layer
  touches it. Use tf2_ros.Buffer.transform(). This is the #1 source of bugs.
  - Latency budgets — track perception loop rate per node. YOLO+depth on GPU: 30 Hz.
  MediaPipe on CPU: 15-30 Hz. VLM: 0.5-2 Hz. Don't put the VLM in a real-time loop.
  - Failure modes per node — what does the node publish when: (a) person leaves frame, (b)
  depth pixel is invalid/zero, (c) model returns no detections? Define these explicitly;
  downstream nodes must tolerate them.
  - Multi-person — design messages as arrays from day one, even if you only test with one
  person.
  - Compute — if you don't have a GPU on the robot computer, lean on MediaPipe (CPU) and
  OAK-D's on-camera inference. YOLO on CPU is ~5 Hz, painful.

