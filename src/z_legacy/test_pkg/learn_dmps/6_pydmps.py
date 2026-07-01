"""
Lesson 6: pydmps — using the library.

We reproduce Lesson 5's experiments using pydmps, to show:
  - Same conceptual workflow, less code
  - Notation crosswalk in action (y, dy, ddy, x for phase, ay/by for alpha_z/beta_z)
  - imitate_path() = learn weights from demo
  - rollout() = generate trajectory from learned weights
  - Changing y0, goal, and tau (time scaling) at rollout time
"""

import numpy as np
import matplotlib.pyplot as plt
import pydmps.dmp_discrete


# ============================================================
# 1. Build a "demo" trajectory (1D, like Lesson 5)
# ============================================================
T_demo = 2.0
dt_demo = 0.01
n_samples = int(T_demo / dt_demo)
t_demo = np.linspace(0, T_demo, n_samples)

# Wiggly "curious" demo: rises with a few peeks
y_demo = (1.0 - np.exp(-2.0 * t_demo)) + 0.15 * np.sin(6 * t_demo) * np.exp(-1.5 * t_demo)

# pydmps wants y_des with shape (n_dmps, n_samples). Here n_dmps = 1.
y_des = y_demo.reshape(1, -1)


# ============================================================
# 2. Create a DMP and learn weights from the demo
# ============================================================
# Note: dt here is the INTERNAL integration timestep used by rollout.
# The library uses a default 'run_time' of 1.0 second, so timesteps = run_time/dt = 100.
dmp = pydmps.dmp_discrete.DMPs_discrete(
    n_dmps=1,         # 1D
    n_bfs=50,         # number of Gaussians  (more = finer detail)
    dt=0.01,          # internal integration timestep
    # ay defaults to 25, by defaults to ay/4 (critical damping). Don't override.
)

# imitate_path returns the trajectory it tried to fit (same as input y_des,
# possibly resampled). The weights are stored in dmp.w (shape: (1, 50)).
y_track = dmp.imitate_path(y_des=y_des, plot=False)


# ============================================================
# 3. Roll out and verify reconstruction
# ============================================================
# IMPORTANT pydmps detail: by default, run_time=1.0 second of phase.
# imitate_path() resamples the demo to fill those internal timesteps.
# So when we rollout(), we get a 1-second trajectory regardless of T_demo.
# To compare apples-to-apples, we map the rollout's time axis to the demo's duration.
y_rollout, dy_rollout, ddy_rollout = dmp.rollout()
# y_rollout has shape (timesteps, n_dmps) — note: time is axis 0 here, axis 1 is the DMPs
# Stretch the rollout time axis from [0, run_time] to [0, T_demo] for plotting:
t_rollout = np.linspace(0, T_demo, y_rollout.shape[0])


# ============================================================
# 4. Replay with NEW start and goal — shape preserved
# ============================================================
dmp.y0 = np.array([0.2])        # new starting position
dmp.goal = np.array([1.8])      # new goal
y_new_sg, _, _ = dmp.rollout()


# ============================================================
# 5. Replay with TIME SCALING via tau
# ============================================================
# Reset to original start/goal for a clean comparison
dmp.y0 = np.array([y_demo[0]])
dmp.goal = np.array([y_demo[-1]])

# tau > 1 makes the motion play SLOWER; tau < 1 plays FASTER.
# This is the magic of the canonical system from Lesson 3.
y_slow, _, _ = dmp.rollout(tau=0.5)   # slower (tau<1 in pydmps means longer)
y_fast, _, _ = dmp.rollout(tau=2.0)   # faster
# In pydmps, tau scales the canonical system time. We stretch axes accordingly.
t_slow = np.linspace(0, T_demo / 0.5, y_slow.shape[0])  # tau=0.5 → 2x duration
t_fast = np.linspace(0, T_demo / 2.0, y_fast.shape[0])  # tau=2.0 → 0.5x duration


# ============================================================
# Plot
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 9))

# Top-left: demo vs reconstruction
ax = axes[0, 0]
ax.plot(t_demo,    y_demo,        'k--', lw=2, label='demo')
ax.plot(t_rollout, y_rollout[:, 0], lw=2, label='pydmps rollout')
ax.set_title("Demo vs. pydmps reconstruction\n(imitate_path + rollout)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

# Top-right: same weights, new start/goal
ax = axes[0, 1]
ax.plot(t_demo,    y_demo,    'k--', alpha=0.4, label='original demo')
t_new = np.linspace(0, T_demo, y_new_sg.shape[0])
ax.plot(t_new, y_new_sg[:, 0], lw=2, color='C2',
        label='same weights, y0=0.2, goal=1.8')
ax.axhline(0.2, color='gray', ls=':', alpha=0.4)
ax.axhline(1.8, color='gray', ls=':', alpha=0.4)
ax.set_title("Spatial generalization\n(personality preserved, range stretched)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

# Bottom-left: time scaling via tau
ax = axes[1, 0]
ax.plot(t_rollout, y_rollout[:, 0], lw=2, label='tau=1.0 (default)')
ax.plot(t_slow,    y_slow[:, 0],    lw=2, label='tau=0.5 (slower)')
ax.plot(t_fast,    y_fast[:, 0],    lw=2, label='tau=2.0 (faster)')
ax.set_title("Time scaling with tau\n(same weights, different durations)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

# Bottom-right: the learned weights
ax = axes[1, 1]
ax.bar(np.arange(dmp.n_bfs), dmp.w[0])
ax.axhline(0, color='gray', alpha=0.5)
ax.set_title(f"Learned weights (dmp.w shape = {dmp.w.shape})\nThis is your emotion vector")
ax.set_xlabel("basis index i"); ax.set_ylabel("w_i")
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# Numerical sanity check — interpolate demo onto rollout's time grid
y_demo_resampled = np.interp(t_rollout, t_demo, y_demo)
err = np.sqrt(np.mean((y_demo_resampled - y_rollout[:, 0])**2))
print("Saved lesson7_output.png")
print()
print(f"Reconstruction RMSE: {err:.4f}")
print(f"Weight vector shape: {dmp.w.shape}  (n_dmps=1, n_bfs=50)")
print(f"ay (= alpha_z): {dmp.ay}")
print(f"by (= beta_z):  {dmp.by}")
print(f"cs.ax (= alpha_s): {dmp.cs.ax}")
print()
print("Summary:")
print("  - imitate_path(y_des) does Lesson 5 in one line.")
print("  - rollout() generates the trajectory.")
print("  - Change dmp.y0 and dmp.goal to retarget; weights stay the same.")
print("  - Pass tau to rollout() for time scaling.")