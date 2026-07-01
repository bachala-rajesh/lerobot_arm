import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# ── 1. Learn one emotion from a demo ─────────────────────────────────────────
# Simulate a "curious" demo: lamp leans forward and tilts head
T = 500
t_demo = np.linspace(0, 1, T)

# Demo was recorded with the lamp at a specific position
demo_y0   = np.array([0.0,  0.0,  0.3,  0.0,  0.0])   # x,y,z,pitch,yaw
demo_goal = np.array([0.1,  0.0,  0.4, -0.3,  0.1])


y_des = np.vstack([
    np.linspace(demo_y0[i], demo_goal[i], T) +
    0.05 * np.sin(2 * np.pi * t_demo * (i + 1))
    for i in range(5)
])

dmp = DMPs_discrete(n_dmps=5, n_bfs=50, dt=0.01)
dmp.imitate_path(y_des=y_des)



print("Learned from demo:")
print(f"  y0   : {np.round(dmp.y0,   3)}")
print(f"  goal : {np.round(dmp.goal, 3)}")
print(f"  w[0] sample: {np.round(dmp.w[0, :3], 3)}")  # weights unchanged throughout

# -------------- retargeting
dmp.reset_state()
y_original, _, _ = dmp.rollout()

# ── 3. Rollout 2 — spatial retargeting (new y0 and goal) ─────────────────────
# The lamp is now at a different pose when "curious" triggers.
# We retarget WITHOUT relearning.

new_y0   = np.array([0.15, 0.05, 0.35,  0.1, -0.05])  # current arm pose
new_goal = np.array([0.25, 0.05, 0.45, -0.2,  0.05])  # new target

dmp.y0 = new_y0
dmp.goal = new_goal


dmp.reset_state()     # reset uses the new y0
y_retargeted, _, _ = dmp.rollout()

print("\nAfter spatial retargeting:")
print(f"  new y0   : {np.round(dmp.y0,   3)}")
print(f"  new goal : {np.round(dmp.goal, 3)}")
print(f"  w[0] sample (unchanged): {np.round(dmp.w[0, :3], 3)}")


# ── 4. Rollout 3 — temporal retargeting (tau) ─────────────────────────────────
# Same new_y0 and new_goal, but play it slower (sad version)
# and faster (surprised version)

tau_slow = 2.0    # 2x slower — "sad curious"
tau_fast = 0.5    # 2x faster — "surprised curious"

dmp.y0   = new_y0
dmp.goal = new_goal

dmp.reset_state()
y_slow, _, _ = dmp.rollout(tau=tau_slow)

dmp.reset_state()
y_fast, _, _ = dmp.rollout(tau=tau_fast)

# ── 5. Plot spatial retargeting ───────────────────────────────────────────────
axis_names = ['x', 'y', 'z', 'pitch', 'yaw']
t = np.linspace(0, dmp.timesteps * dmp.dt, dmp.timesteps)

fig, axes = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
for i, (ax, name) in enumerate(zip(axes, axis_names)):
    ax.plot(t, y_original[:, i],
            color='gray', linewidth=2, linestyle='--', label='original')
    ax.plot(t, y_retargeted[:, i],
            color='steelblue', linewidth=2, label='retargeted')
    ax.set_ylabel(name)
    ax.legend(loc='upper right', fontsize=8)
axes[0].set_title("Spatial retargeting — same weights, new y0 and goal")
axes[-1].set_xlabel("Time (s)")
plt.tight_layout()
plt.savefig("lesson_06_spatial.png", dpi=120)
plt.show()

# ── 6. Plot temporal retargeting (z axis only for clarity) ───────────────────
t_slow = np.linspace(0, len(y_slow) * dmp.dt, len(y_slow))
t_fast = np.linspace(0, len(y_fast) * dmp.dt, len(y_fast))

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(t,      y_retargeted[:, 2], color='steelblue', linewidth=2,
        label='normal (tau=1.0)')
ax.plot(t_slow, y_slow[:, 2],       color='green',     linewidth=2,
        label=f'slow (tau={tau_slow})')
ax.plot(t_fast, y_fast[:, 2],       color='red',       linewidth=2,
        label=f'fast (tau={tau_fast})')
ax.set_xlabel("Time (s)")
ax.set_ylabel("z position")
ax.set_title("Temporal retargeting — same weights, different tau (z axis)")
ax.legend()
plt.tight_layout()
plt.savefig("lesson_06_temporal.png", dpi=120)
plt.show()