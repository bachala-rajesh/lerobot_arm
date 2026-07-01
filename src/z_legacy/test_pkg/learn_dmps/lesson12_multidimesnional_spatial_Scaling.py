import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

T = 500
t = np.linspace(0, 2 * np.pi, T)

radius = 0.1
x_circle = radius * np.cos(t)
z_circle = radius * np.sin(t)

# pitch and yaw have their own small intentional motion
# simulating the head staying oriented correctly during the circle
pitch_demo = 0.1 * np.sin(t)   # small intentional head tilt
yaw_demo   = 0.05 * np.cos(t)  # small intentional yaw

y_des = np.vstack([
    x_circle,
    np.zeros(T),
    z_circle,
    pitch_demo,
    yaw_demo,
])

dmp = DMPs_discrete(n_dmps=5, n_bfs=100, dt=0.01)
dmp.imitate_path(y_des=y_des)
w_base = dmp.w.copy()

scales = [0.5, 1.0, 2.0, 3.0]
colors = ['red', 'gray', 'steelblue', 'green']

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for scale, color in zip(scales, colors):

    # WRONG — uniform scaling
    dmp.w = w_base * scale
    dmp.reset_state()
    y_wrong, _, _ = dmp.rollout()

    # CORRECT — position axes scaled, orientation axes untouched
    axis_scales = np.array([scale, scale, scale, 1.0, 1.0])
    dmp.w = w_base * axis_scales[:, np.newaxis]
    dmp.reset_state()
    y_correct, _, _ = dmp.rollout()

    axes[0].plot(y_wrong[:, 0],   y_wrong[:, 2],
                 color=color, linewidth=2, label=f'scale={scale}')
    axes[1].plot(y_correct[:, 0], y_correct[:, 2],
                 color=color, linewidth=2, label=f'scale={scale}')

# Plot orientation comparison at scale=2.0
fig2, orientation_axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

scale = 2.0

# Wrong
dmp.w = w_base * scale
dmp.reset_state()
y_wrong, _, _ = dmp.rollout()

# Correct
axis_scales = np.array([scale, scale, scale, 1.0, 1.0])
dmp.w = w_base * axis_scales[:, np.newaxis]
dmp.reset_state()
y_correct, _, _ = dmp.rollout()

t_plot = np.linspace(0, dmp.timesteps * dmp.dt, dmp.timesteps)

orientation_axes[0].plot(t_plot, y_wrong[:, 3],
                          color='red', linewidth=2, label='pitch WRONG')
orientation_axes[0].plot(t_plot, y_correct[:, 3],
                          color='steelblue', linewidth=2, label='pitch CORRECT')
orientation_axes[0].set_ylabel("pitch (rad)")
orientation_axes[0].legend()
orientation_axes[0].set_title(
    f"Orientation at scale={scale} — wrong vs correct")

orientation_axes[1].plot(t_plot, y_wrong[:, 4],
                          color='red', linewidth=2, label='yaw WRONG')
orientation_axes[1].plot(t_plot, y_correct[:, 4],
                          color='steelblue', linewidth=2, label='yaw CORRECT')
orientation_axes[1].set_ylabel("yaw (rad)")
orientation_axes[1].legend()
orientation_axes[1].set_xlabel("Time (s)")

for ax in axes:
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_aspect('equal')
    ax.legend(fontsize=8)

axes[0].set_title("WRONG — uniform scale (orientation distorted)")
axes[1].set_title("CORRECT — position scaled, orientation preserved")

plt.tight_layout()
plt.show()