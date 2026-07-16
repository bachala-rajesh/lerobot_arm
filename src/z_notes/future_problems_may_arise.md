# Future Problems That May Arise

Notes on deliberate design choices. If something breaks later, check here first.

---

## 1. The real 6DOF arm is NOT rotated in the world frame

**Date:** 2026-07-16

### The decision

| mode | world_joint rotation |
|------|----------------------|
| Gazebo 6DOF | `rpy = 0 0 -1.5708` (rotated −90°) |
| **Real 6DOF** | `rpy = 0 0 0` (NOT rotated) |

The −90° yaw lives **only** in the Gazebo branch of
`so101_description/urdf/so101_arm_with_control.urdf.xacro`.
The real robot gets `xyz = 0 0 0`, `rpy = 0 0 0`.

### Why the −90° exists

The 6DOF CAD has a different "forward" convention than the 5DOF.
At zero joints:
- 5DOF tip runs down base **−Y**
- 6DOF tip runs down base **+X**

The −90° yaw realigns the 6DOF onto the 5DOF convention — but only in Gazebo.

### Why real mode was left un-rotated

Current AprilTag localization is anchored to the **robot base**, not to a
fixed room/world frame. Proof — `apriltags_localization/config/real_apriltags_config.yaml`:

```yaml
world_frame: "follower_base_link"
```

So the localizer solves `base_link → camera` and places tags in `base_link`
coordinates. Everything is base-relative. The −90° only rotates
`base_link` relative to the URDF `world` frame, which AprilTags never uses.
→ The yaw has **zero effect** on localization. No need to rotate the real arm.

### Symptoms that would mean "revisit this"

Watch for these. They mean sim and real disagree by 90° in the world frame:

- MoveIt goal computed in sim aims 90° off on the real arm.
- `scene_localizer` / `apriltag_world_localizer` outputs 90° rotated.
- You switch to **tags fixed in the room** (walls/table) to find where the
  robot sits in a fixed world → now the world convention matters.
- Any code that mixes the real 6DOF arm's world frame with 5DOF-convention math.

### The clean fix, when needed

Do NOT keep patching per-branch. Instead:

1. Rotate `base_link` **inside** `6dof_so101_arm_fixed.urdf.xacro`
   so both arms share one convention.
2. Then delete the `dof==6` yaw special-case in the placement block.
3. Now real and sim agree everywhere. Check with:
   ```
   ros2 run tf2_ros tf2_echo world follower_base_link
   ```

---

## 2. 6DOF axis signs were negated to match this arm's servo convention

**Date:** 2026-07-16

`6dof_so101_arm_fixed.urdf.xacro` — pan, wrist_yaw, wrist_roll axes were
negated (plus elbow_flex, wrist_flex earlier). Upstream CAD
(PathOn-AI repo) zeroes the servos the opposite way to our 5DOF arm on every
joint except `shoulder_lift`.

- **Proven on hardware:** elbow_flex, wrist_flex.
- **Proven by 5DOF cross-check:** shoulder_pan, wrist_roll.
- **INFERRED, not proven:** `wrist_yaw` (no 5DOF twin to compare). If it
  renders backwards, negate its axis back and nothing else moves.
- **Untouched:** gripper (5DOF is revolute, 6DOF is prismatic — not comparable).

Backup of the original 6DOF file (before axis edits) is in git:
```
git show HEAD:src/so101_description/urdf/robots/6dof_so101_arm.urdf.xacro
```

---

## 3. 6DOF base sank 3 cm into the Gazebo table

**Date:** 2026-07-16

Both arms were placed at `z = 0.97`, but the 5DOF mesh sits 3 cm above its
own `base_link` (visual origin `z=0.0301`, rolled +90°) while the 6DOF mesh
starts at its origin. Same number, 6DOF buried 3 cm → table top is at `z=1.0`
→ `shoulder_pan` drove the base sideways through solid table → joint frozen.

**Fix:** Gazebo 6DOF now placed at `z = 1.0` (see placement block).
If a future mesh export changes the base origin, re-check this offset.
