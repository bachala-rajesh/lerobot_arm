# lesson_03_imitate_path.py
# Goal: Understand imitate_path() deeply — what it expects, what it does
#       internally, and how to handle real demos of arbitrary duration.

import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# ─────────────────────────────────────────────────────────────────────────────
# PART 1: What shape does y_des need to be?
# ─────────────────────────────────────────────────────────────────────────────
# y_des must be shape (n_dmps, T) — axes as ROWS, timesteps as COLUMNS.
# This is the OPPOSITE of what you'd naturally get from numpy recording
# (which gives you shape (T, n_dmps)).
# pydmps will transpose internally if you pass (T, 1) for 1D, but for
# multi-dim you must get this right. We'll be explicit.

print("=" * 55)
print("PART 1 — Shape of y_des")
print("=" * 55)

# Synthetic demo: a smooth bump trajectory (not just a straight line)
# so we can see that the weights actually capture shape.
T_demo = 500   # number of demo timesteps (arbitrary)
t_demo = np.linspace(0, 1, T_demo)

# A smooth trajectory from 0 → 1 with a bump in the middle
y_demo_1d = t_demo + 0.3 * np.sin(2 * np.pi * t_demo)

# Shape must be (n_dmps, T) = (1, 500)
y_des = y_demo_1d.reshape(1, -1)
print(f"y_des shape: {y_des.shape}")   # must be (1, T_demo)
print(f"y_des[0, 0]  (start): {y_des[0, 0]:.4f}")
print(f"y_des[0, -1] (end)  : {y_des[0, -1]:.4f}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# PART 2: THE NORMALIZATION GOTCHA
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 55)
print("PART 2 — The normalization gotcha")
print("=" * 55)

# Instantiate with default run_time (1.0s) and dt (0.01s) → 100 timesteps
dmp = DMPs_discrete(n_dmps=1, n_bfs=50, dt=0.01)
print(f"DMP timesteps : {dmp.timesteps}")    # 100
print(f"DMP dt        : {dmp.dt}")           # 0.01
print(f"DMP run_time  : {dmp.timesteps * dmp.dt:.3f}s")

# imitate_path() receives y_des with T_demo=500 points.
# Internally it does ONE thing before fitting weights:
#   y_des is resampled to exactly dmp.timesteps points.
# So 500 demo points → 100 DMP points. Duration info is THROWN AWAY.
# The DMP just knows: "this shape goes from y_des[0] to y_des[-1]
#  in run_time=1.0s". It has no memory that your demo was 3 seconds.

dmp.imitate_path(y_des=y_des)

print(f"\nAfter imitate_path:")
print(f"  dmp.w shape : {dmp.w.shape}")     # (1, 50)
print(f"  dmp.y0      : {dmp.y0}")          # set from y_des[0]
print(f"  dmp.goal    : {dmp.goal}")        # set from y_des[-1]
print()

# ─────────────────────────────────────────────────────────────────────────────
# PART 3: Rollout and compare to demo
# ─────────────────────────────────────────────────────────────────────────────
dmp.reset_state()
y_track, dy_track, _ = dmp.rollout()

# The DMP timeline is always 0 → run_time (1.0s here)
t_dmp = np.linspace(0, dmp.timesteps * dmp.dt, dmp.timesteps)

# The demo timeline — notice it's ALSO normalized to 0→1 for comparison
t_demo_normalized = np.linspace(0, 1.0, T_demo)

fig, axes = plt.subplots(2, 1, figsize=(9, 6))

axes[0].plot(t_demo_normalized, y_demo_1d,
             color='gray', linewidth=2, linestyle='--', label='demo')
axes[0].plot(t_dmp, y_track[:, 0],
             color='steelblue', linewidth=2, label='DMP reproduction')
axes[0].set_ylabel("Position")
axes[0].set_title("DMP imitate_path() — reproduction vs demo")
axes[0].legend()

axes[1].bar(range(dmp.n_bfs), dmp.w[0], color='steelblue', alpha=0.7)
axes[1].set_xlabel("Basis function index")
axes[1].set_ylabel("Weight value")
axes[1].set_title("Learned weights  dmp.w[0]  (the 'emotion DNA')")

plt.tight_layout()
plt.savefig("lesson_03_part1.png", dpi=120)
# plt.show()




# ─────────────────────────────────────────────────────────────────────────────
# PART 4: Handling real demo duration — the correct pattern
# ─────────────────────────────────────────────────────────────────────────────

demo_duration_real = 2.4    # seconds
demo_hz            = 50     # Hz
T_real             = int(demo_duration_real * demo_hz)  # 120 samples

t_real = np.linspace(0, demo_duration_real, T_real)
y_real = np.sin(np.pi * t_real / demo_duration_real)

# In your version of pydmps, duration is controlled via dt alone.
# timesteps is computed internally as: timesteps = int(1.0 / dt)
# So to get a DMP that plays for demo_duration_real seconds,
# set dt = demo_duration_real / desired_timesteps

desired_timesteps  = 240
dt_correct         = demo_duration_real / desired_timesteps   # 0.01s

dmp_correct = DMPs_discrete(n_dmps=1, n_bfs=50, dt=dt_correct)

print(f"Correct DMP dt        : {dmp_correct.dt:.4f}s")
print(f"Correct DMP timesteps : {dmp_correct.timesteps}")
print(f"Correct DMP run_time  : {dmp_correct.timesteps * dmp_correct.dt:.3f}s")

y_des_real = y_real.reshape(1, -1)
dmp_correct.imitate_path(y_des=y_des_real)
dmp_correct.reset_state()
y_track_correct, _, _ = dmp_correct.rollout()

# WRONG: default dt=0.01 → timesteps=100 → run_time=1.0s (too fast)
dmp_wrong = DMPs_discrete(n_dmps=1, n_bfs=50, dt=0.01)
dmp_wrong.imitate_path(y_des=y_des_real)
dmp_wrong.reset_state()
y_track_wrong, _, _ = dmp_wrong.rollout()

t_correct = np.linspace(0, dmp_correct.timesteps * dmp_correct.dt,
                         dmp_correct.timesteps)
t_wrong   = np.linspace(0, dmp_wrong.timesteps * dmp_wrong.dt,
                         dmp_wrong.timesteps)

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(t_real,    y_real,
        color='gray', linestyle='--', linewidth=2,
        label=f'demo ({demo_duration_real}s real)')
ax.plot(t_correct, y_track_correct[:, 0],
        color='steelblue', linewidth=2,
        label=f'correct DMP ({dmp_correct.timesteps * dmp_correct.dt:.1f}s)')
ax.plot(t_wrong,   y_track_wrong[:, 0],
        color='red', linewidth=2, linestyle=':',
        label='wrong DMP (1.0s, too fast)')
ax.set_xlabel("Time (s)")
ax.set_ylabel("Position")
ax.set_title("Duration handling: correct vs wrong")
ax.legend()
plt.tight_layout()
plt.savefig("lesson_03_part2.png", dpi=120)
plt.show()
