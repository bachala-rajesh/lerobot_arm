# lesson_02_internals.py
# Goal: Inspect everything inside a pydmps DMPs_discrete object.

import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# ── 1. Instantiate (same as Lesson 1) ────────────────────────────────────────
dmp = DMPs_discrete(n_dmps=1, n_bfs=10)  # n_bfs=10 so printouts are readable

# ── 2. Weights ────────────────────────────────────────────────────────────────
print("=" * 50)
print("WEIGHTS  dmp.w")
print("=" * 50)
print(f"  Shape : {dmp.w.shape}")   # (n_dmps, n_bfs)
print(f"  Values: {dmp.w}")         # all zeros — nothing learned yet
print()
# WHY shape is (n_dmps, n_bfs):
#   Row i = weight vector for axis i.
#   For your lamp: 5 rows (x, y, z, pitch, yaw), n_bfs columns.
#   Blending two emotions = weighted average of two such matrices.

# ── 3. Basis function centers and widths ─────────────────────────────────────
print("=" * 50)
print("BASIS FUNCTION CENTERS  dmp.c")
print("=" * 50)
print(f"  Shape : {dmp.c.shape}")   # (n_bfs,) — shared across all axes
print(f"  Values: {np.round(dmp.c, 4)}")
print()

print("=" * 50)
print("BASIS FUNCTION WIDTHS  dmp.h")
print("=" * 50)
print(f"  Shape : {dmp.h.shape}")   # (n_bfs,) — shared across all axes
print(f"  Values: {np.round(dmp.h, 4)}")
print()
# WHY centers are shared:
#   All axes use ONE canonical system (one phase variable s).
#   The Gaussians are placed along s-space, not time.
#   Each axis gets its own WEIGHTS on those shared Gaussians.

# ── 4. Canonical system ───────────────────────────────────────────────────────
print("=" * 50)
print("CANONICAL SYSTEM  dmp.cs")
print("=" * 50)
print(f"  Type      : {type(dmp.cs)}")
print(f"  alpha_s   : {dmp.cs.ax}")     # controls phase decay speed
print(f"  run_time  : {dmp.cs.run_time}")
print(f"  dt        : {dmp.cs.dt}")
print(f"  timesteps : {dmp.cs.timesteps}")
print()

# Manually roll out the phase variable to see its shape
s_track = dmp.cs.rollout()
print(f"  Phase s_track shape: {s_track.shape}")
print(f"  s at t=0   : {s_track[0]:.6f}")    # should be 1.0
print(f"  s at t=end : {s_track[-1]:.6f}")   # should be near 0.0
print()

# ── 5. Goal and start ─────────────────────────────────────────────────────────
print("=" * 50)
print("GOAL and START")
print("=" * 50)
print(f"  dmp.y0   : {dmp.y0}")
print(f"  dmp.goal : {dmp.goal}")
print()

# ── 6. Visualize basis functions in phase space ───────────────────────────────
# This is what the forcing function "sees" — Gaussians tiling s-space.
s = s_track  # phase values from 1 → 0

psi_matrix = np.zeros((len(s), dmp.n_bfs))
for i in range(dmp.n_bfs):
    psi_matrix[:, i] = np.exp(-dmp.h[i] * (s - dmp.c[i])**2)

fig, axes = plt.subplots(2, 1, figsize=(9, 6))

# Plot each basis function against phase s
for i in range(dmp.n_bfs):
    axes[0].plot(s, psi_matrix[:, i])
axes[0].set_xlabel("Phase s  (1 → 0)")
axes[0].set_ylabel("ψ(s)")
axes[0].set_title(f"Basis functions in phase space  (n_bfs={dmp.n_bfs})")
axes[0].invert_xaxis()   # s starts at 1, ends at 0 — left-to-right is time

# Same thing but plotted against time index so it looks like a timeline
t = np.arange(len(s))
for i in range(dmp.n_bfs):
    axes[1].plot(t, psi_matrix[:, i])
axes[1].set_xlabel("Timestep")
axes[1].set_ylabel("ψ(s)")
axes[1].set_title("Same basis functions vs time")

plt.tight_layout()
plt.savefig("lesson_02_output.png", dpi=120)
plt.show()
print("Plot saved to lesson_02_output.png")