# lesson_05_step.py
# Goal: Reproduce rollout() manually using step(), then sketch
#       the ROS2 control loop pattern.

import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# ── 1. Learn a 5-axis emotion ─────────────────────────────────────────────────
T = 500
t_demo = np.linspace(0, 1, T)

y_des = np.vstack([
    0.3 * t_demo,
    0.05 * np.sin(2 * np.pi * t_demo),
    0.2  * np.sin(np.pi * t_demo),
    -0.4 * t_demo + 0.2 * np.sin(2 * np.pi * t_demo),
    0.1  * np.sin(4 * np.pi * t_demo),
])

dmp = DMPs_discrete(n_dmps=5, n_bfs=50, dt=0.01)
dmp.imitate_path(y_des=y_des)

axis_names = ['x', 'y', 'z', 'pitch', 'yaw']

# ── 2. Reproduce rollout() manually using step() ──────────────────────────────
print("Running manual step() loop...")

dmp.reset_state()

n_steps = dmp.timesteps
y_manual   = np.zeros((n_steps, 5))
dy_manual  = np.zeros((n_steps, 5))

for i in range(n_steps):
    y, dy, ddy = dmp.step()   # advance one timestep
    y_manual[i]  = y          # y is shape (5,)
    dy_manual[i] = dy

print(f"y_manual shape : {y_manual.shape}")   # (100, 5)

# ── 3. Compare to rollout() ───────────────────────────────────────────────────
dmp.reset_state()
y_rollout, _, _ = dmp.rollout()

max_diff = np.max(np.abs(y_manual - y_rollout))
print(f"Max difference between step() and rollout(): {max_diff:.2e}")
# Should be ~0.0 — they are identical

# ── 4. Plot step() output ─────────────────────────────────────────────────────
t = np.linspace(0, n_steps * dmp.dt, n_steps)

fig, axes = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
for i, (ax, name) in enumerate(zip(axes, axis_names)):
    ax.plot(t, y_manual[:, i], color='steelblue', linewidth=2,
            label='step()')
    ax.plot(t, y_rollout[:, i], color='red', linewidth=1,
            linestyle='--', label='rollout()')
    ax.set_ylabel(name)
    ax.legend(loc='upper right', fontsize=8)
axes[0].set_title("step() vs rollout() — should be identical")
axes[-1].set_xlabel("Time (s)")
plt.tight_layout()
plt.savefig("lesson_05_output.png", dpi=120)
plt.show()

