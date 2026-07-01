import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# Learn a shape from a demo
T = 200
y_demo = np.sin(np.pi * np.linspace(0, 1, T))

dmp = DMPs_discrete(n_dmps=1, n_bfs=50, dt=0.01)
dmp.imitate_path(y_demo.reshape(1, -1))

default_duration = dmp.timesteps * dmp.dt
print(f"Default duration : {default_duration}s")
print(f"DMP timesteps    : {dmp.timesteps}")

target_durations = [0.5, 1.0, 2.4]
results = {}

for target in target_durations:
    tau = target / default_duration
    print(f"\ntarget={target}s → tau={tau}")

    dmp.reset_state()
    y_track, _, _ = dmp.rollout(tau=tau)

    # print what we actually got back
    print(f"  y_track.shape = {y_track.shape}")

    # build time axis from ACTUAL returned length, not dmp.timesteps
    actual_steps = y_track.shape[0]
    t = np.linspace(0, target, actual_steps)
    results[target] = (t, y_track[:, 0])

fig, ax = plt.subplots(figsize=(9, 4))
colors = ['red', 'steelblue', 'green']
for (target, (t, y)), color in zip(results.items(), colors):
    ax.plot(t, y, color=color, linewidth=2, label=f'tau → {target}s')

ax.set_xlabel("Real time (s)")
ax.set_ylabel("Position")
ax.set_title("Same weights, same shape — different duration via tau")
ax.legend()
plt.tight_layout()
plt.show()