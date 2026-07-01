import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete


T= 500
t = np.linspace(0, 1, T)

# Each axis gets a distinct shape — like a real "curious" emotion
# where x moves forward, z dips then rises, pitch tilts, etc.
x_demo     =  0.3 * t                              # slow forward drift
y_demo     =  0.05 * np.sin(2 * np.pi * t)         # small lateral wobble
z_demo     =  0.2 * np.sin(np.pi * t)              # arc up then down
pitch_demo = -0.4 * t + 0.2 * np.sin(2*np.pi*t)   # tilt forward with wobble
yaw_demo   =  0.1 * np.sin(4 * np.pi * t)

# stack into shape (n_dmps, T)
y_des = np.vstack([x_demo, y_demo, z_demo, pitch_demo, yaw_demo])
print(f"y_des.shape = {y_des.shape}")

# instantiante dmps
N_AXES = y_des.shape[0]
dmp = DMPs_discrete(n_dmps=N_AXES, n_bfs=50, dt=0.01)


print(f"\nBefore imitate_path:")
print(f"  dmp.w shape  : {dmp.w.shape}")    # (5, 50)
print(f"  dmp.y0 shape : {dmp.y0.shape}")   # (5,)
print(f"  dmp.goal shape: {dmp.goal.shape}")# (5,)


dmp.imitate_path(y_des = y_des)
print(f"\nAfter imitate_path:")
print(f"  dmp.y0   : {np.round(dmp.y0,   4)}")   # start of each axis
print(f"  dmp.goal : {np.round(dmp.goal, 4)}")   # end of each axis
print(f"  dmp.w[0] (x)     first 5 weights: {np.round(dmp.w[0,:5], 3)}")
print(f"  dmp.w[2] (z)     first 5 weights: {np.round(dmp.w[2,:5], 3)}")
print(f"  dmp.w[3] (pitch) first 5 weights: {np.round(dmp.w[3,:5], 3)}")

dmp.reset_state()
y_track, dy_track, _ = dmp.rollout()

print(f"\ny_track shape: {y_track.shape}")   # (timesteps, 5)

axis_names = ['x', 'y', 'z', 'pitch', 'yaw']
t_dmp  = np.linspace(0, dmp.timesteps * dmp.dt, dmp.timesteps)
t_demo = np.linspace(0, 1.0, T)

# ── 5. Plot: demo vs reproduction for all 5 axes ──────────────────────────────
fig, axes = plt.subplots(N_AXES, 1, figsize=(10, 12), sharex=True)

demo_signals = [x_demo, y_demo, z_demo, pitch_demo, yaw_demo]

for i, (ax, name, demo) in enumerate(zip(axes, axis_names, demo_signals)):
    ax.plot(t_demo, demo,
            color='gray', linewidth=2, linestyle='--', label='demo')
    ax.plot(t_dmp, y_track[:, i],
            color='steelblue', linewidth=2, label='DMP')
    ax.set_ylabel(name)
    ax.legend(loc='upper right', fontsize=8)
    if i == 0:
        ax.set_title("5-axis DMP: demo vs reproduction (one phase, 5 weight rows)")

axes[-1].set_xlabel("Time (s)")
plt.tight_layout()
plt.savefig("lesson_04_output.png", dpi=120)
plt.show()


# ── 6. Prove the phase is shared ──────────────────────────────────────────────
print("\nKey check — canonical system is shared:")
print(f"  dmp.cs.ax : {dmp.cs.ax}")   # one alpha_s for all axes
s_track = dmp.cs.rollout()
print(f"  s_track shape : {s_track.shape}")  # (timesteps,) — ONE phase
print(f"  s start : {s_track[0]:.4f}")       # 1.0
print(f"  s end   : {s_track[-1]:.6f}")      # near 0
print("\nAll 5 axes driven by this single phase variable.")