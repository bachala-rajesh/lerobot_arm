import numpy as np
import matplotlib.pyplot as plt

from pydmps.dmp_discrete import DMPs_discrete

# instantiate DMPs_discrete object
dmp = DMPs_discrete(
    n_dmps=1,         # 1D
    n_bfs=100)

# set start and goal
dmp.y0 = np.array([0.0])        # starting position
dmp.goal = np.array([1.0])      # goal

# reset internal state
dmp.reset_state()


# rollout
y_track, dy_track, ddy_track = dmp.rollout()

print(f"Trajectory shape: {y_track.shape}")   # expect (timesteps, 1)
print(f"Start value:  {y_track[0, 0]:.4f}")   # should be ~0.0
print(f"Final value:  {y_track[-1, 0]:.4f}")  # should be ~1.0
print(f"DMP timesteps: {dmp.timesteps}")
print(f"DMP dt:        {dmp.dt}")
print(f"DMP run_time:  {dmp.timesteps * dmp.dt:.3f}s")

# plot
t = np.linspace(0, dmp.timesteps * dmp.dt, dmp.timesteps)

fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)

axes[0].plot(t, y_track[:, 0], color='steelblue', linewidth=2)
axes[0].axhline(dmp.goal[0], color='red', linestyle='--', label='goal')
axes[0].axhline(dmp.y0[0],   color='green', linestyle='--', label='start')
axes[0].set_ylabel("Position")
axes[0].legend()
axes[0].set_title("DMP Trajectory (no learned weights — pure attractor)")

axes[1].plot(t, dy_track[:, 0], color='orange', linewidth=2)
axes[1].set_ylabel("Velocity")

axes[2].plot(t, ddy_track[:, 0], color='purple', linewidth=2)
axes[2].set_ylabel("Acceleration")
axes[2].set_xlabel("Time (s)")

plt.tight_layout()
plt.savefig("lesson_01_output.png", dpi=120)
plt.show()

