"""
Discrete vs rhythmic DMPs in pydmps.

We fit the SAME shape with both DMP flavors and compare:
  - Discrete: runs once, settles at goal
  - Rhythmic: repeats the pattern indefinitely
"""

import numpy as np
import matplotlib.pyplot as plt
import pydmps.dmp_discrete
import pydmps.dmp_rhythmic


# ============================================================
# 1. Demo 1: a "reach with overshoot" — naturally a DISCRETE motion
# ============================================================
n_samples = 200
t_demo = np.linspace(0, 1, n_samples)
y_reach = 1.0 - np.exp(-3 * t_demo) * np.cos(2 * np.pi * t_demo)

dmp_d = pydmps.dmp_discrete.DMPs_discrete(n_dmps=1, n_bfs=30, dt=0.01)
dmp_d.imitate_path(y_des=y_reach.reshape(1, -1))

# Roll out enough to see what happens AFTER the motion "completes"
dmp_d.timesteps = 300  # 3 seconds at dt=0.01
y_d, _, _ = dmp_d.rollout()


# ============================================================
# 2. Demo 2: one cycle of a "sway" — naturally a RHYTHMIC motion
# ============================================================
# Single cycle of a sway (this is what you'd record: one period of the motion)
y_sway = 0.3 * np.sin(2 * np.pi * t_demo) + 0.1 * np.sin(4 * np.pi * t_demo)

dmp_r = pydmps.dmp_rhythmic.DMPs_rhythmic(n_dmps=1, n_bfs=30, dt=0.01)
dmp_r.imitate_path(y_des=y_sway.reshape(1, -1))

# Roll out for 3 cycles
dmp_r.timesteps = 600
y_r, _, _ = dmp_r.rollout()


# ============================================================
# 3. Cross-experiment: what if we fit the SWAY with a DISCRETE DMP?
#    Spoiler: it tries to converge to the last sample (goal), losing periodicity.
# ============================================================
dmp_d_on_sway = pydmps.dmp_discrete.DMPs_discrete(n_dmps=1, n_bfs=30, dt=0.01)
dmp_d_on_sway.imitate_path(y_des=y_sway.reshape(1, -1))
dmp_d_on_sway.timesteps = 300
y_d_on_sway, _, _ = dmp_d_on_sway.rollout()


# ============================================================
# Plot
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 8))

# Discrete fit, discrete behavior
ax = axes[0, 0]
ax.plot(np.arange(len(y_reach)) * 0.01, y_reach, 'k--', lw=2, label='demo (1 cycle)')
ax.plot(np.arange(len(y_d)) * 0.01, y_d[:, 0], 'C0', lw=2, label='discrete DMP rollout')
ax.axhline(y_reach[-1], color='gray', ls=':', alpha=0.5, label='goal')
ax.axvline(1.0, color='red', ls=':', alpha=0.4, label='demo length')
ax.set_title("Discrete DMP on a 'reach' demo\n(runs once, settles at goal)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

# Rhythmic fit, rhythmic behavior
ax = axes[0, 1]
ax.plot(np.arange(len(y_sway)) * 0.01, y_sway, 'k--', lw=2, label='demo (1 cycle)')
ax.plot(np.arange(len(y_r)) * 0.01, y_r[:, 0], 'C2', lw=2, label='rhythmic DMP rollout')
ax.axvline(1.0, color='red', ls=':', alpha=0.4, label='1 cycle length')
ax.set_title("Rhythmic DMP on a 'sway' demo\n(repeats forever)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

# Wrong tool for the job: discrete on rhythmic
ax = axes[1, 0]
ax.plot(np.arange(len(y_sway)) * 0.01, y_sway, 'k--', lw=2, label='demo (1 cycle of sway)')
ax.plot(np.arange(len(y_d_on_sway)) * 0.01, y_d_on_sway[:, 0], 'C3', lw=2,
        label='discrete DMP (wrong tool!)')
ax.axhline(y_sway[-1], color='gray', ls=':', alpha=0.5, label='goal = last sample')
ax.set_title("DISCRETE DMP fitted to SWAY demo\n(does not repeat — converges to last point)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

# Concept: idle + emotion overlay
ax = axes[1, 1]
t_compose = np.arange(len(y_r)) * 0.01
# Pad y_d with its final value so we can sum
y_d_padded = np.full_like(y_r[:, 0], y_d[-1, 0])
y_d_padded[:len(y_d)] = y_d[:, 0]
# Use rhythmic as 'idle baseline' (small amplitude) + discrete as 'emotion overlay'
idle_amp = 0.15
discrete_amp = 0.7
y_combined = idle_amp * y_r[:, 0] + discrete_amp * y_d_padded
ax.plot(t_compose, idle_amp * y_r[:, 0], 'C2', alpha=0.5, lw=1.5, label='idle (rhythmic, scaled)')
ax.plot(t_compose, discrete_amp * y_d_padded, 'C0', alpha=0.5, lw=1.5, label='emotion (discrete, scaled)')
ax.plot(t_compose, y_combined, 'k', lw=2, label='combined output')
ax.set_title("Lamp runtime: rhythmic idle + discrete emotion\n(this is the real-world composition)")
ax.set_xlabel("time [s]"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

print()
print("Observations:")
print("  Top-left: discrete DMP fitted to a one-shot reach. Settles at goal after 1s.")
print("  Top-right: rhythmic DMP fitted to one cycle of sway. Repeats forever.")
print("  Bottom-left: WRONG TOOL — discrete DMP on a sway demo loses the oscillation.")
print("  Bottom-right: Real lamp runtime — small rhythmic idle + larger discrete emotion.")