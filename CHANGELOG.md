# CHANGELOG

## How to use this file

Update this file at **milestones only** — not every commit.
A milestone is: a working feature, a deployment, a major fix, a major refactor.

Format per entry:
- Date + short title
- Added / Changed / Fixed / Removed sections
- Keep each line short — one idea per line

For small day-to-day changes → rely on git commit messages.
For bugs found and root causes → log in `src/problems_faced.md`.

---

## 2026-07-01 — Workspace maintenance: package renames + cleanup

### Changed
- `so101_interfaces` → `project_interfaces` (fixed internal msg cross-refs across all dependents)
- `so101_teleop` → `joy_teleop` (generic name, not robot-specific)
- `s0101_moveit_5dof` → `so101_moveit_5dof` (fixed typo: zero vs letter o)
- `so101_6dof_moveit_config` → `so101_moveit_6dof` (naming consistency)
- `vlm` → `vlm_perception` (more descriptive)
- URDF DOF argument: `dof_type` → `dof`, values `dof_5`/`dof_6` → `5`/`6` (applied across 20 files)
- `so101_bringup`: 17 launch files renamed to consistent `{env}_{who}_{ctrl}.launch.py` pattern
- `oakd_camera`: 3 active launch files renamed (`real`, `sim_rsp`, `sim_pointcloud`)

### Added
- `README.md` added to every package
- `src/Changes.md` — detailed one-time log of this session
- `moveit_commander/TODO.md` — note on 6DOF support needed

### Removed / moved to legacy
- 4 unused `oakd_camera` launch files → `oakd_camera/legacy/`
- `debug_moveit_config.py` (empty file) → `so101_bringup/legacy/`
- `scene_db/test_db.py` → `scene_db/legacy/`
- `so101_description` old 6DOF URDF → `so101_description/legacy/`
- `so101_control` boilerplate linter test stubs deleted

### Fixed
- `scene.db` removed from git tracking (runtime data should not be in version control)
- `*.db` added to workspace `.gitignore`
- All `package.xml` files: version 0.0.0 → 0.1.0, license TODO → Apache-2.0, maintainer placeholders fixed
- All `CMakeLists.txt`: removed C++ compiler flags block + `BUILD_TESTING` lint block from Python-only packages

---

## [template for next entry]

## YYYY-MM-DD — short title

### Added
-

### Changed
-

### Fixed
-

### Removed
-
