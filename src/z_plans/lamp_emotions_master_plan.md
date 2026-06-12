# Lamp Emotions — Master Project Plan
### Pixar-style Expressive Robotic Arm using LeRobot SO-100

---

> **How to use this document**
> - **Part 1** — read before writing any code. Understand the full picture.
> - **Part 2** — follow step by step during implementation. Never skip a step.
> - **Part 3** — read when a layer is working. Pick variants to extend it.

---

# PART 1 — Layer Plan and Architecture

## System Overview

```
┌─────────────────────────────────────────────┐
│         Layer 3B — Director                 │  decides what to express
│   rule system → neural net → LLM            │
├─────────────────────────────────────────────┤
│         Layer 3A — Perception               │  observes the world
│   keyboard → camera → depth → VLM           │
├─────────────────────────────────────────────┤
│         Layer 2 — Grammar                   │  makes sentences
│   blend → sequence → transition → mood      │
├─────────────────────────────────────────────┤
│         Layer 1 — Vocabulary                │  motion words
│   DMP fitting → weight storage → variants   │
├─────────────────────────────────────────────┤
│         Layer 0 — Recording                 │  raw data
│   teleoperation → HDF5 → index              │
├─────────────────────────────────────────────┤
│         Execution Layer (always on)         │  physical motion
│   IK solver → safety → MoveIt2 → SO-100    │
└─────────────────────────────────────────────┘
```

---

## Layer 0 — Recording (Motion Capture)

**What it is:** The data collection foundation. Records
teleoperated demonstrations and stores them in structured
format. Has no intelligence. Only observes and stores.

**Inputs:** Teleoperation via leader arm
**Outputs:** HDF5 files + index.json

**Key components:**
- `recorder.py` — live recording with keyboard controls
- `verifier.py` — quality checking and plotting
- `exporter.py` — exports clean arrays for Layer 1
- `index.json` — auto-maintained registry of all recordings

**Data stored per episode:**
- Joint positions (5 joints, 50Hz)
- Joint velocities (5 joints, 50Hz)
- End-effector pose (x,y,z,pitch,yaw, computed via FK)
- Timestamps
- Metadata (emotion, notes, date, quality)

**Status before moving to Layer 1:**
All emotions recorded with 5+ variants each. All verified.
All exported. index.json accurate.

---

## Layer 1 — Vocabulary (DMP Library)

**What it is:** Converts raw recorded trajectories into
mathematical motion representations (DMPs). Stores learned
weights. This is the motion vocabulary — individual words.

**Inputs:** Exported .npz files from Layer 0
**Outputs:** DMP weight files (.npz) per variant per emotion

**Key components:**
- `dmp_fitter.py` — normalises demos, fits DMPs, saves weights
- `dmp.py` — SingleJointDMP class (one per joint)
- `weight_store.py` — load/save/query weights by emotion + variant

**What DMP fitting does:**
1. Load raw joint trajectory (T×5 array)
2. Time-normalise to 200 points (removes duration variation)
3. Fit one DMP per joint using `pydmps.imitate_path()`
4. Save weights array (n_joints × n_basis_functions)
5. Update index.json with dmp_fitted=true

**Status before moving to Layer 2:**
All variants fitted. Replay of any variant from weights
matches original demonstration visually.

---

## Layer 2 — Grammar (Motion Composition)

**What it is:** Combines vocabulary into expressive sentences.
Handles blending between emotions, sequencing of motions,
timing, transitions, and global mood colouring.

**Inputs:** Emotion commands from Layer 3B
**Outputs:** Cartesian pose stream at 50Hz to Execution Layer

**Key components:**
- `blender.py` — interpolates DMP weights across variants
- `sequencer.py` — chains emotions with timing
- `normaliser.py` — time-warps trajectories
- `transition.py` — crossfades between active emotions
- `mood.py` — global speed/amplitude modifier
- `rhythm.py` — pacing and timing engine

**Status before moving to Layer 3:**
Blending between two emotions works smoothly.
Transitions do not cause arm jerks.
Mood modifier visibly changes motion character.

---

## Layer 3A — Perception

**What it is:** Observes the world and converts raw sensor
data into structured events. Never makes decisions.
Only observes and emits events.

**Inputs:** Camera, depth camera, keyboard, ROS2 topics, timer
**Outputs:** Structured events {type, intensity, position, context}

**Key components:**
- `perception.py` — main perception node
- `sensors/keyboard.py` — keyboard trigger handler
- `sensors/depth_camera.py` — Open3D point cloud processing
- `sensors/rgb_camera.py` — face/object detection

**Status before moving to Layer 3B:**
At minimum keyboard triggers work and emit correct events.
Camera perception is optional at this stage.

---

## Layer 3B — Director

**What it is:** Receives structured events from Layer 3A
and decides what the lamp should express. The brain of
the system. Start with rules, evolve to neural net or LLM.

**Inputs:** Events from Layer 3A
**Outputs:** Emotion commands {emotion, variant_hint, intensity, duration}

**Key components:**
- `director.py` — main decision logic
- `rules.py` — rule-based director (Phase C)
- `llm_director.py` — VLM/LLM director (Phase D)

**Status before calling complete:**
Lamp reacts meaningfully to perceived events.
Emotions feel contextually appropriate.

---

## Execution Layer (runs always, built once)

**What it is:** Converts Cartesian pose stream into physical
arm motion. Handles IK, safety, and MoveIt2 communication.
Built once in Phase A. Never touched again.

**Key components:**
- `ik_solver.py` — MoveIt2 IK wrapper
- `safety.py` — joint limit clamping, velocity cap
- `main_loop.py` — 50Hz control loop

---

## Build Sequence Overview

```
Phase A — Layer 0 + Execution    weeks 1-2
Phase B — Layer 1                week 3
Phase C — Layer 2 core           weeks 4-5
Phase D — Layer 3 simple         week 6
Phase E — Layer 3 camera         weeks 7-8
Phase F — Layer 3 intelligent    weeks 9-10
```

---

# PART 2 — Handheld Implementation Guide

---

## Phase A — Layer 0 and Execution Foundation

### Goal
Record demonstrations of all emotions. Confirm full pipeline
from recording through to arm moving on real hardware.

---

### Step A1 — Create project structure

```bash
cd ~/ros2_ws/src
mkdir -p lamp_emotions/lamp_emotions/{layer0/sensors,layer1,layer2,layer3/sensors,execution,emotions}
mkdir -p lamp_emotions/lamp_emotions/layer0/{recordings,weights}
touch lamp_emotions/lamp_emotions/__init__.py
touch lamp_emotions/lamp_emotions/layer0/__init__.py
touch lamp_emotions/lamp_emotions/layer1/__init__.py
touch lamp_emotions/lamp_emotions/layer2/__init__.py
touch lamp_emotions/lamp_emotions/layer3/__init__.py
touch lamp_emotions/lamp_emotions/execution/__init__.py
touch lamp_emotions/lamp_emotions/emotions/__init__.py
```

Create `package.xml` and `setup.py` for the ROS2 package.

**Test:** `colcon build --packages-select lamp_emotions` succeeds.

---

### Step A2 — Build BaseEmotion class

File: `lamp_emotions/emotions/base.py`

```python
from abc import ABC, abstractmethod
import numpy as np

class BaseEmotion(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.t      = 0.0
        self.done   = False

    @abstractmethod
    def step(self, current_pose: np.ndarray,
             dt: float) -> np.ndarray:
        """
        INPUT:  current_pose shape(5,) [x,y,z,pitch,yaw]
                dt float seconds
        OUTPUT: next_pose   shape(5,) [x,y,z,pitch,yaw]
        """
        pass

    def reset(self):
        self.t    = 0.0
        self.done = False

    # helpers available to all plugins
    def _sine(self, amp, freq, phase=0.0):
        return amp * np.sin(2*np.pi*freq*self.t + phase)

    def _envelope(self, duration):
        return max(0.0, 1.0 - (self.t / duration)**2)

    def _noise(self, scale, speed, seed=0.0):
        from noise import pnoise1
        return scale * pnoise1(self.t * speed + seed)
```

**Test:** Import works. Instantiating a concrete subclass works.

---

### Step A3 — Build Execution Layer

File: `lamp_emotions/execution/ik_solver.py`

This wraps MoveIt2 IK. It receives a Cartesian pose
(x,y,z,pitch,yaw) and returns joint angles.

```python
import rclpy
from moveit_msgs.srv import GetPositionIK
from geometry_msgs.msg import PoseStamped
import numpy as np

class IKSolver:
    def __init__(self, node):
        self.node   = node
        self.client = node.create_client(
            GetPositionIK, '/compute_ik')
        self.client.wait_for_service(timeout_sec=5.0)

    def solve(self, pose_xyzpy: np.ndarray):
        """
        pose_xyzpy: [x, y, z, pitch, yaw] in metres/degrees
        returns: joint_angles shape(5,) or None if failed
        """
        req = self._build_request(pose_xyzpy)
        future = self.client.call_async(req)
        rclpy.spin_until_future_complete(self.node, future)
        resp = future.result()
        if resp.error_code.val == 1:   # SUCCESS
            return np.array(resp.solution.joint_state.position)
        return None

    def _build_request(self, pose):
        # convert pose array to PoseStamped
        # convert pitch/yaw to quaternion
        # fill GetPositionIK request
        ...
```

File: `lamp_emotions/execution/safety.py`

```python
import numpy as np

# SO-100 joint limits in degrees
JOINT_LIMITS = [
    (-180, 180),   # joint1 base rotation
    (-120, 120),   # joint2 main lean
    (-120, 120),   # joint3 mid segment
    (-120, 120),   # joint4 head tilt
    (-180, 180),   # joint5 head pan
]

MAX_VELOCITY_DEG_PER_SEC = 60.0

def clamp_joints(angles, prev_angles, dt):
    safe = []
    for i, (angle, prev) in enumerate(
            zip(angles, prev_angles)):
        lo, hi  = JOINT_LIMITS[i]
        angle   = np.clip(angle, lo, hi)
        max_d   = MAX_VELOCITY_DEG_PER_SEC * dt
        angle   = prev + np.clip(
            angle - prev, -max_d, max_d)
        safe.append(angle)
    return np.array(safe)
```

**Test:** Move arm to a known pose via IK. Confirm it arrives.
Confirm safety clamping prevents exceeding limits.

---

### Step A4 — Build IdleEmotion plugin

File: `lamp_emotions/emotions/idle.py`

Simplest possible plugin. Pure Perlin noise. No DMP.
Confirms the whole pipeline runs end to end.

```python
import numpy as np
from lamp_emotions.emotions.base import BaseEmotion

class IdleEmotion(BaseEmotion):

    def __init__(self, config):
        super().__init__(config)
        self.base_pose = np.array(
            config.get('base_pose',
                       [0.10, 0.00, 0.30, 0.0, 0.0]))

    def step(self, current_pose, dt):
        self.t += dt

        noise = np.array([
            self._noise(0.005, 0.8, seed=0.0),  # x drift
            self._noise(0.003, 1.1, seed=10.0), # y drift
            self._noise(0.004, 0.6, seed=20.0), # z drift
            self._noise(1.0,   0.5, seed=30.0), # pitch
            self._noise(0.8,   0.7, seed=40.0), # yaw
        ])

        return self.base_pose + noise
```

**Test:** Arm runs idle. Moves with slow organic micro-motion.
Never stops dead. Never jerks.

---

### Step A5 — Build main loop

File: `lamp_emotions/main_loop.py`

```python
import rclpy
import time
import numpy as np
from lamp_emotions.emotions.idle import IdleEmotion
from lamp_emissions.execution.ik_solver import IKSolver
from lamp_emotions.execution.safety import clamp_joints

DT = 0.02  # 50Hz

def main():
    rclpy.init()
    node = rclpy.create_node('lamp_emotions')

    ik      = IKSolver(node)
    emotion = IdleEmotion(config={})
    prev_joints = np.zeros(5)

    while rclpy.ok():
        t_start = time.time()

        current_pose  = ik.get_current_pose()
        next_pose     = emotion.step(current_pose, DT)
        joint_angles  = ik.solve(next_pose)

        if joint_angles is not None:
            safe_joints = clamp_joints(
                joint_angles, prev_joints, DT)
            ik.send_joints(safe_joints)
            prev_joints = safe_joints

        elapsed = time.time() - t_start
        time.sleep(max(0, DT - elapsed))

if __name__ == '__main__':
    main()
```

**Test:** Idle runs on real arm for 60 seconds without error.
Timing stays close to 50Hz. No joint limit violations.

---

### Step A6 — Build recorder.py

File: `lamp_emotions/layer0/recorder.py`

**What it connects to:**
```
ROS2 topic: /follower/joint_states  (sensor_msgs/JointState)
```

**Keyboard controls:**
```
SPACE  — start / stop recording
P      — preview (replay last recording)
S      — save to HDF5
D      — discard
Q      — quit
```

**Terminal display (updates 10Hz):**
```
Emotion: curiosity   Variant: v03
Status:  RECORDING   Duration: 2.34s   Samples: 117

Joint angles (degrees):
  J1:  23.4    J2:  45.1    J3: -12.3
  J4:  -8.7    J5:   4.2

End-effector:
  x: 0.142   y: 0.003   z: 0.318

Controls: SPACE=stop  S=save  D=discard  Q=quit
```

**On save — writes HDF5:**
```
/metadata/emotion_name
/metadata/variant_number
/metadata/recorded_at
/metadata/duration_seconds
/metadata/sample_rate_hz
/metadata/operator_notes
/follower/joint_positions    (T, 5) float32
/follower/joint_velocities   (T, 5) float32
/follower/timestamps         (T,)   float64
/cartesian/end_effector_pose (T, 5) float32
```

**On save — updates index.json automatically.**

**Run it:**
```bash
python -m lamp_emotions.layer0.recorder \
    --emotion curiosity \
    --notes "slow lean forward"
```

**Test:** Record 3 demos. Check HDF5 files exist.
Open in Python with h5py and inspect manually.
Confirm index.json has correct entries.

---

### Step A7 — Build verifier.py

File: `lamp_emotions/layer0/verifier.py`

```bash
# check all variants of one emotion
python -m lamp_emotions.layer0.verifier \
    --emotion curiosity

# show plots
python -m lamp_emotions.layer0.verifier \
    --emotion curiosity --plot

# check specific variant
python -m lamp_emotions.layer0.verifier \
    --emotion curiosity --variant 2
```

**Output:**
```
curiosity — 5 variants found

v01  2.3s  115 samples  50.0Hz  ✓ good
v02  1.8s   90 samples  50.0Hz  ✓ good
v03  0.4s   20 samples  50.0Hz  ⚠ too short (< 0.5s)
v04  2.1s  105 samples  49.8Hz  ✓ good
v05  8.4s  420 samples  50.0Hz  ⚠ very long (> 8s)

Warnings: 2 variants need attention
```

**Quality checks:**
- Duration < 0.5s → warn: too short for DMP fitting
- Duration > 8.0s → warn: very long, consider trimming
- Any joint at limit → warn: joint limit reached
- Sample rate < 40Hz → warn: recording gaps detected
- Velocity spikes > 300°/s → warn: jerky motion detected

**Test:** Run on all recorded emotions. Fix any warnings.
Target: all variants show ✓ good before moving to Layer 1.

---

### Step A8 — Build exporter.py

File: `lamp_emotions/layer0/exporter.py`

```bash
python -m lamp_emotions.layer0.exporter \
    --emotion curiosity \
    --output layer1/demonstrations/
```

Exports one .npz per variant:
```python
np.savez(output_path,
    joint_positions  = arr_T5,
    joint_velocities = arr_T5,
    timestamps       = arr_T,
    end_effector     = arr_T5,
    metadata         = metadata_dict)
```

**Test:** Load exported file in numpy. Confirm shapes correct.
Confirm values match original HDF5.

---

### Step A9 — Record all emotions

For each emotion below, record minimum 5 variants:

| Emotion | Target duration | Key motion quality |
|---|---|---|
| idle | 4-8s | slow organic sway |
| curiosity | 1.5-3s | lean forward, head tilt |
| surprised | 0.5-1.5s | fast recoil backward |
| sad | 2-4s | slow droop, low energy |
| happy | 1-2s | upright, light bounce |
| no_shake | 1.5-2.5s | lateral oscillation ×3-4 |
| yes_nod | 1-2s | forward-back dip ×1-2 |
| shy | 2-4s | slow retreat, turn away |
| excited | 1-2s | fast bouncy up-down |
| thinking | 3-6s | slow circular wander |

**Phase A complete when:**
- [ ] All 10 emotions recorded, 5+ variants each
- [ ] All variants verified clean (no warnings)
- [ ] All exported to layer1/demonstrations/
- [ ] Idle runs on real arm for 60s without issues
- [ ] index.json accurate and complete

---

## Phase B — Layer 1: DMP Fitting

### Goal
Convert all raw recordings into DMP weight files.
Verify replay matches demonstrations.

---

### Step B1 — Build DMP wrapper

File: `lamp_emotions/layer1/dmp.py`

Thin wrapper over pydmps for one joint:

```python
import pydmps.dmp_discrete
import numpy as np

class SingleJointDMP:
    def __init__(self, n_bfs=20, alpha=25.0):
        beta = alpha / 4.0
        self.dmp = pydmps.dmp_discrete.DMPs_discrete(
            n_dmps=1,
            n_bfs=n_bfs,
            ay=np.array([alpha]),
            by=np.array([beta]),
        )

    def fit(self, trajectory):
        """trajectory: 1D array, normalised to 200 points"""
        self.dmp.imitate_path(
            y_des=trajectory.reshape(1, -1))

    def rollout(self, start, goal, duration, dt=0.02):
        self.dmp.y0   = np.array([start])
        self.dmp.goal = np.array([goal])
        self.dmp.reset_state()
        steps = int(duration / dt)
        traj = []
        for _ in range(steps):
            y, _, _ = self.dmp.step()
            traj.append(float(y[0]))
        return np.array(traj)

    @property
    def weights(self):
        return self.dmp.w.copy()

    @weights.setter
    def weights(self, w):
        self.dmp.w = w.copy()
```

---

### Step B2 — Build dmp_fitter.py

File: `lamp_emotions/layer1/dmp_fitter.py`

```python
from scipy.interpolate import interp1d
import numpy as np

def normalise_trajectory(traj, target_length=200):
    """time-warp any length trajectory to target_length points"""
    original = np.linspace(0, 1, len(traj))
    target   = np.linspace(0, 1, target_length)
    f = interp1d(original, traj, kind='cubic')
    return f(target)

def fit_emotion(emotion_name, demo_dir, weights_dir):
    demos = load_all_demos(emotion_name, demo_dir)

    for variant_id, demo in demos.items():
        joint_positions = demo['joint_positions']  # (T, 5)
        weights_per_joint = []

        for j in range(5):
            raw  = joint_positions[:, j]
            norm = normalise_trajectory(raw, 200)
            dmp  = SingleJointDMP(n_bfs=20, alpha=25.0)
            dmp.fit(norm)
            weights_per_joint.append(dmp.weights)

        save_weights(
            emotion_name, variant_id,
            weights_per_joint, weights_dir)

        update_index(emotion_name, variant_id,
                     dmp_fitted=True)
        print(f"  fitted {emotion_name}/{variant_id}")
```

**Run:**
```bash
python -m lamp_emotions.layer1.dmp_fitter \
    --emotion curiosity
# or fit all emotions at once
python -m lamp_emotions.layer1.dmp_fitter --all
```

---

### Step B3 — Build weight_store.py

File: `lamp_emotions/layer1/weight_store.py`

```python
import numpy as np
import json
from pathlib import Path

class WeightStore:

    def __init__(self, weights_dir):
        self.weights_dir = Path(weights_dir)

    def save(self, emotion, variant_id, weights, metadata):
        path = self.weights_dir / emotion / f"{variant_id}.npz"
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path,
            weights  = np.array(weights),  # (5, n_bfs)
            metadata = json.dumps(metadata))

    def load(self, emotion, variant_id):
        path = self.weights_dir / emotion / f"{variant_id}.npz"
        data = np.load(path, allow_pickle=True)
        return data['weights'], json.loads(
            str(data['metadata']))

    def load_all(self, emotion):
        """load all variants for one emotion"""
        folder = self.weights_dir / emotion
        variants = {}
        for f in folder.glob('*.npz'):
            vid = f.stem
            variants[vid] = self.load(emotion, vid)
        return variants

    def list_emotions(self):
        return [p.name for p in self.weights_dir.iterdir()
                if p.is_dir()]
```

---

### Step B4 — Verify DMP replay

Write a quick replay test:

```python
# replay_test.py
store  = WeightStore('layer1/weights')
solver = IKSolver(node)

weights, meta = store.load('curiosity', 'v01')

# build 5 DMPs (one per joint)
dmps = []
for j in range(5):
    dmp = SingleJointDMP()
    dmp.weights = weights[j]
    dmps.append(dmp)

# rollout
current_joints = solver.get_current_joints()
for step in range(100):
    joint_targets = [
        dmp.rollout_step() for dmp in dmps]
    solver.send_joints(joint_targets)
    time.sleep(0.02)
```

**Test:** Replay curiosity v01. Does it look like your
original demonstration? It will not be identical but
should feel similar. Repeat for 3 emotions.

**Phase B complete when:**
- [ ] All emotions fitted, weights saved
- [ ] Replay of each emotion recognisably matches demo
- [ ] index.json updated with dmp_fitted=true for all
- [ ] Weight files loadable and shapes correct (5 × n_bfs)

---

## Phase C — Layer 2: Grammar

### Goal
Blend between emotions smoothly. Add transitions.
Add global mood modifier.

---

### Step C1 — Build blender.py

File: `lamp_emotions/layer2/blender.py`

Linear interpolation between DMP weights:

```python
import numpy as np

class WeightBlender:

    def blend_two(self, weights_a, weights_b, alpha):
        """
        alpha=0.0 → pure A
        alpha=1.0 → pure B
        """
        return (1 - alpha) * weights_a + alpha * weights_b

    def blend_many(self, weights_list, alphas):
        """
        weights_list: list of (5, n_bfs) arrays
        alphas: list of floats summing to 1.0
        """
        assert abs(sum(alphas) - 1.0) < 1e-6
        result = np.zeros_like(weights_list[0])
        for w, a in zip(weights_list, alphas):
            result += a * w
        return result
```

**Test:** Blend curiosity and surprised at alpha=0.5.
Replay blended weights. Does it feel like something
between the two? It should.

---

### Step C2 — Build transition.py

File: `lamp_emotions/layer2/transition.py`

Crossfades between outgoing and incoming emotion:

```python
import numpy as np

class TransitionManager:

    def __init__(self, duration=0.3):
        self.duration    = duration
        self.t           = 0.0
        self.in_progress = False
        self.outgoing    = None
        self.incoming    = None

    def start(self, outgoing_emotion, incoming_emotion):
        self.outgoing    = outgoing_emotion
        self.incoming    = incoming_emotion
        self.t           = 0.0
        self.in_progress = True

    def step(self, current_pose, dt):
        if not self.in_progress:
            return self.incoming.step(current_pose, dt)

        self.t += dt
        alpha = min(1.0, self.t / self.duration)

        pose_out = self.outgoing.step(current_pose, dt)
        pose_in  = self.incoming.step(current_pose, dt)

        # smooth crossfade using cosine
        w = 0.5 * (1 - np.cos(np.pi * alpha))
        blended = (1 - w) * pose_out + w * pose_in

        if alpha >= 1.0:
            self.in_progress = False

        return blended
```

**Test:** Trigger curiosity. After 1s trigger surprised.
Watch transition. Should feel smooth, no jerk.

---

### Step C3 — Build mood.py

File: `lamp_emotions/layer2/mood.py`

Global modifier that colours all emotions:

```python
import numpy as np

class MoodState:

    MOODS = {
        'neutral':   {'speed': 1.0, 'amplitude': 1.0, 'noise': 1.0},
        'tired':     {'speed': 0.5, 'amplitude': 0.6, 'noise': 0.4},
        'energetic': {'speed': 1.5, 'amplitude': 1.3, 'noise': 1.5},
        'anxious':   {'speed': 1.2, 'amplitude': 0.8, 'noise': 2.0},
        'calm':      {'speed': 0.7, 'amplitude': 0.9, 'noise': 0.3},
    }

    def __init__(self):
        self.current = 'neutral'

    def set(self, mood_name):
        assert mood_name in self.MOODS
        self.current = mood_name

    def apply(self, pose_delta, dt):
        """apply mood modifier to a pose change"""
        params = self.MOODS[self.current]
        return pose_delta * params['amplitude']

    def get_speed_scale(self):
        return self.MOODS[self.current]['speed']
```

**Test:** Run curiosity in neutral mood then tired mood.
Should visibly feel different — tired version slower
and smaller amplitude.

---

### Step C4 — Build sequencer.py

File: `lamp_emotions/layer2/sequencer.py`

Chains emotions in order with timing:

```python
import time

class Sequencer:

    def __init__(self, behaviour_manager):
        self.manager  = behaviour_manager
        self.sequence = []
        self.index    = 0
        self.active   = False

    def load(self, sequence):
        """
        sequence: list of dicts
        [
          {'emotion': 'curious',  'duration': 2.0},
          {'emotion': 'surprised','duration': 1.5},
          {'emotion': 'shy',      'duration': 3.0},
        ]
        """
        self.sequence = sequence
        self.index    = 0
        self.active   = True
        self._trigger_current()

    def update(self):
        if not self.active:
            return
        current = self.sequence[self.index]
        if self.manager.current_emotion_done():
            self.index += 1
            if self.index >= len(self.sequence):
                self.active = False
                return
            self._trigger_current()

    def _trigger_current(self):
        step = self.sequence[self.index]
        self.manager.trigger(step['emotion'])
```

**Test:** Run sequence [curious → surprised → shy].
Confirm each emotion plays fully before next starts.

---

### Step C5 — Wire Layer 2 into main loop

Update `main_loop.py` to include:
- TransitionManager between emotions
- MoodState modifier
- BehaviourManager that holds active emotion

**Phase C complete when:**
- [ ] Blending between two emotions produces natural result
- [ ] Transitions between emotions are smooth
- [ ] Mood modifier visibly changes motion character
- [ ] Sequence of 3 emotions plays correctly
- [ ] 50Hz loop holds timing with all components running

---

## Phase D — Layer 3: Simple Director

### Goal
Lamp reacts to keyboard input via rule-based director.
Full system runs end to end.

---

### Step D1 — Build perception.py (keyboard)

File: `lamp_emotions/layer3/perception.py`

```python
import threading
import queue

class PerceptionNode:

    def __init__(self):
        self.event_queue = queue.Queue()
        self._start_keyboard_listener()

    def _start_keyboard_listener(self):
        key_map = {
            'c': ('emotion_trigger', 'curiosity',  0.8),
            's': ('emotion_trigger', 'surprised',  1.0),
            'h': ('emotion_trigger', 'happy',      0.7),
            'n': ('emotion_trigger', 'no_shake',   0.9),
            'y': ('emotion_trigger', 'yes_nod',    0.8),
            'a': ('emotion_trigger', 'sad',        0.6),
            'e': ('emotion_trigger', 'excited',    1.0),
            'i': ('emotion_trigger', 'idle',       0.5),
            'q': ('quit',            None,          0.0),
        }

        def listen():
            import termios, tty, sys
            fd  = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch in key_map:
                        etype, emotion, intensity = key_map[ch]
                        self.event_queue.put({
                            'type':      etype,
                            'emotion':   emotion,
                            'intensity': intensity,
                            'position':  None,
                        })
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        t = threading.Thread(target=listen, daemon=True)
        t.start()

    def get_events(self):
        events = []
        while not self.event_queue.empty():
            events.append(self.event_queue.get())
        return events
```

---

### Step D2 — Build director.py (rule-based)

File: `lamp_emotions/layer3/director.py`

```python
class RuleDirector:

    def process(self, events, current_emotion, mood):
        for event in events:

            if event['type'] == 'emotion_trigger':
                return {
                    'emotion':      event['emotion'],
                    'intensity':    event['intensity'],
                    'variant_hint': 'auto',
                    'duration':     None,
                }

            if event['type'] == 'person_close':
                if event['distance'] < 0.3:
                    return {'emotion': 'surprised',
                            'intensity': 1.0}
                else:
                    return {'emotion': 'curious',
                            'intensity': 0.6}

            if event['type'] == 'no_activity':
                return {'emotion': 'idle',
                        'intensity': 0.3}

        return None  # no change
```

---

### Step D3 — Wire full system

Update `main_loop.py`:

```python
perception = PerceptionNode()
director   = RuleDirector()
manager    = BehaviourManager(plugins, config)
mood       = MoodState()
transition = TransitionManager()
ik         = IKSolver(node)

while rclpy.ok():
    t_start = time.time()

    events  = perception.get_events()
    command = director.process(
        events, manager.active_emotion, mood)

    if command:
        manager.trigger(command['emotion'])

    current_pose = ik.get_current_pose()
    next_pose    = transition.step(current_pose, DT)
    joint_angles = ik.solve(next_pose)

    if joint_angles is not None:
        safe = clamp_joints(joint_angles, prev_joints, DT)
        ik.send_joints(safe)
        prev_joints = safe

    time.sleep(max(0, DT - (time.time() - t_start)))
```

**Test:** Press each key. Lamp transitions to correct emotion.
Transitions smooth. No jerks. Full loop at 50Hz.

**Phase D complete when:**
- [ ] All 10 emotions triggerable by keyboard
- [ ] Transitions smooth between all emotion pairs
- [ ] 50Hz holds with full pipeline
- [ ] System runs 10 minutes without crash or error

---

## Phase E — Layer 3A: Depth Camera

### Goal
Lamp perceives the world through depth camera.
Reacts to presence, position, and movement of people.

---

### Step E1 — Setup and calibration

Install dependencies:
```bash
pip install open3d pyrealsense2
```

Verify camera publishes:
```bash
ros2 topic list | grep camera
# expect:
# /camera/depth/image_raw
# /camera/color/image_raw
# /camera/depth/points
```

Run hand-eye calibration:
- Use MoveIt2 hand-eye calibration package
- Moves arm to known positions
- Computes transform from camera frame to robot base frame
- Save transform as camera_to_base.yaml

---

### Step E2 — Build depth_camera.py

File: `lamp_emotions/layer3/sensors/depth_camera.py`

```python
import open3d as o3d
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2

class DepthCameraPerception:

    def __init__(self, node, camera_to_base_transform):
        self.transform = camera_to_base_transform
        self.sub = node.create_subscription(
            PointCloud2, '/camera/depth/points',
            self._callback, 10)
        self.latest_events = []

    def _callback(self, msg):
        pcd = self._ros_to_open3d(msg)
        pcd = self._transform_to_robot_frame(pcd)
        pcd = self._filter_background(pcd)
        clusters = self._cluster(pcd)
        self.latest_events = self._classify(clusters)

    def _ros_to_open3d(self, msg):
        import sensor_msgs_py.point_cloud2 as pc2
        points = np.array([
            [p[0], p[1], p[2]]
            for p in pc2.read_points(msg, skip_nans=True)
        ])
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        return pcd

    def _filter_background(self, pcd):
        # remove floor and wall points
        # keep only points in front of robot
        pts = np.asarray(pcd.points)
        mask = (
            (pts[:, 2] > 0.1) &   # above floor
            (pts[:, 0] > 0.0) &   # in front
            (pts[:, 0] < 1.5)     # within range
        )
        filtered = o3d.geometry.PointCloud()
        filtered.points = o3d.utility.Vector3dVector(
            pts[mask])
        return filtered

    def _cluster(self, pcd):
        labels = np.array(pcd.cluster_dbscan(
            eps=0.05, min_points=20))
        clusters = []
        for label in set(labels):
            if label < 0:
                continue
            mask = labels == label
            pts  = np.asarray(pcd.points)[mask]
            c = o3d.geometry.PointCloud()
            c.points = o3d.utility.Vector3dVector(pts)
            clusters.append(c)
        return clusters

    def _classify(self, clusters):
        events = []
        for cluster in clusters:
            centroid = np.mean(
                np.asarray(cluster.points), axis=0)
            distance = np.linalg.norm(centroid)
            events.append({
                'type':     'object_detected',
                'position': centroid.tolist(),
                'distance': float(distance),
            })
        return events

    def get_events(self):
        return self.latest_events.copy()
```

---

### Step E3 — Integrate into perception.py

Add DepthCameraPerception as a second input source:

```python
class PerceptionNode:
    def __init__(self, node):
        self.keyboard = KeyboardPerception()
        self.camera   = DepthCameraPerception(
            node, load_transform('camera_to_base.yaml'))

    def get_events(self):
        return (self.keyboard.get_events() +
                self.camera.get_events())
```

**Test:** Stand in front of lamp. Lamp should detect you
and trigger curiosity. Move closer — should trigger surprised.
Move away — should return to idle.

**Phase E complete when:**
- [ ] Camera events flowing into perception correctly
- [ ] Lamp tracks detected person with curiosity
- [ ] Distance-based emotion scaling works
- [ ] System stable with camera running at full framerate

---

## Phase F — Layer 3B: Intelligent Director

### Goal
Replace rule-based director with VLM or LLM.
Lamp understands scene context, not just raw events.

---

### Step F1 — Build LLM director

File: `lamp_emotions/layer3/llm_director.py`

Uses local VLM (LLaVA or Qwen-VL) or API:

```python
import base64
import requests

class LLMDirector:

    SYSTEM_PROMPT = """
You are the director of an expressive robotic lamp.
Given a description of what the camera sees and recent events,
choose what emotion the lamp should express.

Available emotions: idle, curiosity, surprised, sad, happy,
no_shake, yes_nod, shy, excited, thinking

Respond with JSON only:
{"emotion": "curiosity", "intensity": 0.7, "reason": "..."}
"""

    def process(self, events, scene_image=None):
        scene_description = self._describe_events(events)
        prompt = f"Scene: {scene_description}\nChoose emotion:"

        response = self._call_llm(prompt, scene_image)
        return self._parse_response(response)

    def _call_llm(self, prompt, image=None):
        # call local Ollama or OpenAI API
        ...

    def _describe_events(self, events):
        descriptions = []
        for e in events:
            if e['type'] == 'object_detected':
                descriptions.append(
                    f"Object at {e['distance']:.1f}m")
        return '. '.join(descriptions) or "No activity"
```

**Test:** Show lamp various scenes. Does it choose
contextually appropriate emotions? Refine system prompt
until choices feel natural.

---

# PART 3 — Variants for Each Layer

---

## Layer 0 Variants

**Recording variants:**
- Standard teleoperation (leader arm)
- Kinesthetic teaching (physically move follower arm directly)
- Motion capture markers on arm, record human expression
- Programmatically generated demonstrations (for very clean
  reference trajectories like pure sine waves)

**Storage variants:**
- HDF5 (recommended — binary, fast, metadata support)
- ROS2 bag files (natural if already using ROS2, replayable)
- CSV (human readable, slow for large recordings)
- LeRobot native dataset format (best for ACT/Diffusion Policy)

**Quality variants:**
- Manual quality rating by operator
- Automated quality scoring (smoothness, duration, joint range)
- DTW (Dynamic Time Warping) similarity score between variants
- Automatic outlier detection and flagging

---

## Layer 1 Variants

**DMP variants:**
- Discrete DMP (what we use — point to point)
- Rhythmic DMP (for periodic motions like no_shake natively)
- Cartesian DMP (works in xyz space, joints via IK)
- ProMP (Probabilistic Movement Primitives — models
  distribution of motions, not just one trajectory)

**Fitting variants:**
- Single demo fitting (fast, simple)
- Average of multiple demos (cleaner, less noise)
- Gaussian Process fitting (models uncertainty across demos)
- Neural network encoding (encode trajectory as latent vector)

**Storage variants:**
- .npz files (recommended — fast numpy native)
- SQLite database (queryable, good for large collections)
- Redis (in-memory, fastest retrieval, lost on restart)
- JSON (human readable, slow for large weight arrays)

**Basis function variants:**
- 10 basis functions (fast, coarse)
- 20 basis functions (recommended — good balance)
- 50 basis functions (fine detail, slower fitting)
- 100+ basis functions (very fine, risk of overfitting)

---

## Layer 2 Variants

**Blending variants:**
- Linear interpolation (simple, fast)
- Spherical linear interpolation SLERP (better for rotations)
- Gaussian-weighted blending (weight by similarity to context)
- Learned blending (neural net learns which blend looks natural)

**Transition variants:**
- Linear crossfade (basic)
- Cosine crossfade (recommended — smooth ease in/out)
- Spring-based transition (physically natural)
- Zero-velocity waypoint (stop briefly between emotions)

**Mood variants:**
- Discrete moods (neutral, tired, energetic, anxious, calm)
- Continuous mood space (2D valence-arousal model)
- Learned mood from context (neural net predicts mood)
- Time-of-day mood (lamp naturally more active in morning)

**Sequencing variants:**
- Fixed sequence (predetermined order)
- Probabilistic sequence (weighted random next emotion)
- Reactive sequence (next emotion depends on environment)
- Narrative sequence (story arc with beginning, middle, end)

**Rhythm variants:**
- Fixed timing (each emotion plays for fixed duration)
- Completion-based (emotion signals done, then next)
- Beat-based (sync emotion changes to audio beat)
- Adaptive timing (slow down if person is watching closely)

---

## Layer 3A Perception Variants

**Input source variants:**
- Keyboard (simplest — for development and demo)
- ROS2 topic (receive from any other node)
- RGB camera + OpenCV (face detection, colour detection)
- Depth camera + Open3D (3D position, distance, gesture)
- Microphone + audio processing (sound level, speech detected)
- Web API (receive emotion triggers from phone or web app)
- LeapMotion (hand tracking)
- MQTT (IoT integration — smart home triggers)

**Processing variants:**
- Raw distance threshold (simple, fast)
- DBSCAN clustering (robust object detection in point cloud)
- MediaPipe (hand and pose detection from RGB)
- YOLOv8 (fast object detection with class labels)
- OpenPose (skeleton tracking for gesture recognition)
- Segment Anything (SAM) (precise object segmentation)

---

## Layer 3B Director Variants

**Decision logic variants:**

Simple rule system (Phase D):
```
person_close AND distance < 0.3 → surprised
person_detected AND distance > 0.3 → curious
no_activity AND timeout > 30s → idle
```

Finite state machine (Phase D+):
- Explicit states with transition conditions
- More structured than raw rules
- Easy to reason about and debug

Behaviour tree (Phase D++):
- Industry standard for robot behaviour
- Composable, reusable behaviour nodes
- py_trees library in Python

Reinforcement learning (advanced):
- Train director on recorded human reactions
- Reward = human engagement, response, smile
- Learns what expressions work in what contexts

VLM director (Phase F):
- Camera image → LLaVA/GPT-4V → emotion choice
- Natural language reasoning about scene
- Slow (1-2s latency) so plan ahead

LLM with memory (Phase F+):
- Director remembers recent interaction history
- Builds narrative arc across longer interactions
- Lamp feels like it has personality over time

---

## Execution Layer Variants

**IK solver variants:**
- MoveIt2 KDL solver (default, reliable)
- TRAC-IK (faster, better near limits)
- bio_ik (handles null space optimisation)
- Custom analytical IK (fastest, specific to SO-100 geometry)

**Control mode variants:**
- Position control (what SO-100 supports natively)
- Velocity control (smoother for continuous tracking)
- Impedance control (compliant, safe for human contact)
- Torque control (requires hardware that supports it)

**Safety variants:**
- Joint limit clamping (what we build — essential)
- Velocity limiting (essential)
- Workspace bounding (keep end-effector in safe volume)
- Singularity avoidance (detect and escape singular configs)
- Collision checking (MoveIt2 scene collision)
- Emergency stop on force threshold (requires force sensor)

---

## Cross-Layer Variants — Advanced Extensions

**After all layers work, these become possible:**

**Imitation learning upgrade:**
Replace DMP Layer 1 with ACT (Action Chunking Transformer)
trained on your Layer 0 demonstrations via LeRobot.
Gives more natural variation than DMP replay.

**Emotion transfer:**
Train a small network to transfer emotion style from one
base motion to another. Demonstrates "curious" style
applied to a "greeting" motion base.

**Audience adaptation:**
Layer 3B learns which emotions get positive reactions
from observed humans (via camera). Reinforces successful
expressions over time.

**Multi-lamp ensemble:**
Run two SO-100 arms as a pair. Coordinate emotions
between them for a dialogue or duet performance.

**Sound generation:**
Add speaker output. Each emotion triggers characteristic
sounds (gentle hum for curious, sharp click for surprised).
Synchronise with motion for multimodal expression.

---

*End of Master Plan*

---

**Quick reference — build status tracker**

| Phase | What | Status |
|---|---|---|
| A | Layer 0 recording + Execution + Idle | not started |
| B | Layer 1 DMP fitting + replay | not started |
| C | Layer 2 blending + transitions + mood | not started |
| D | Layer 3 keyboard + rule director | not started |
| E | Layer 3 depth camera | not started |
| F | Layer 3 intelligent VLM director | not started |

Update this table as you progress.
