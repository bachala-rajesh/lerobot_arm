import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# Record a circle in x-z plane
T = 500
t = np.linspace(0, 2 * np.pi, T)

radius = 0.1
x_circle = radius * np.cos(t)
z_circle = radius * np.sin(t)

y_des = np.vstack([
    x_circle,
    np.zeros(T),
    z_circle,
    np.zeros(T),
    np.zeros(T),
])

# Learn once
dmp = DMPs_discrete(n_dmps=5, n_bfs=100, dt=0.01)
dmp.imitate_path(y_des=y_des)
w_base = dmp.w.copy()

# Rollout at different scales
scales = [0.5, 1.0, 2.0, 3.0]
colors = ['red', 'gray', 'steelblue', 'green']

fig, ax = plt.subplots(figsize=(8, 8))

for scale, color in zip(scales, colors):
    dmp.w = w_base * scale
    dmp.reset_state()
    y_track, _, _ = dmp.rollout()

    ax.plot(y_track[:, 0], y_track[:, 2],
            color=color, linewidth=2, label=f'scale={scale}')

ax.set_xlabel("x")
ax.set_ylabel("z")
ax.set_title("Circle scaling via weight multiplication")
ax.legend()
ax.set_aspect('equal')
plt.tight_layout()
plt.show()