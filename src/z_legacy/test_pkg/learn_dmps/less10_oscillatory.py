# lesson_09_rhythmic.py
import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete
from pydmps.dmp_rhythmic import DMPs_rhythmic

# ── 1. Build a breathing cycle demo ──────────────────────────────────────────
T_cycle = 200
t_cycle = np.linspace(0, 2 * np.pi, T_cycle)

# Scale idle to be comparable to emotion amplitude
z_breath     =  0.08 * np.sin(t_cycle)
pitch_breath =  0.1  * np.sin(t_cycle)
zero         =  np.zeros(T_cycle)

y_des_rhythmic = np.vstack([
    zero,
    zero,
    z_breath,
    pitch_breath,
    zero,
])

print("Rhythmic demo shape:", y_des_rhythmic.shape)

# ── 2. Fit rhythmic DMP ───────────────────────────────────────────────────────
dmp_idle = DMPs_rhythmic(n_dmps=5, n_bfs=50, dt=0.01)
dmp_idle.imitate_path(y_des=y_des_rhythmic)

print(f"Rhythmic DMP timesteps : {dmp_idle.timesteps}")
print(f"Rhythmic DMP dt        : {dmp_idle.dt}")
print(f"One cycle duration     : {dmp_idle.timesteps * dmp_idle.dt:.2f}s")

# ── 3. Rollout for multiple cycles via step() ─────────────────────────────────
N_CYCLES = 4
n_steps  = dmp_idle.timesteps * N_CYCLES

dmp_idle.reset_state()
y_idle = np.zeros((n_steps, 5))
for i in range(n_steps):
    y, _, _ = dmp_idle.step()
    y_idle[i] = y

t_idle = np.linspace(0, n_steps * dmp_idle.dt, n_steps)
print(f"\nIdle z range     : {y_idle[:, 2].min():.4f} to {y_idle[:, 2].max():.4f}")
print(f"Idle pitch range : {y_idle[:, 3].min():.4f} to {y_idle[:, 3].max():.4f}")

# ── 4. Learn discrete emotion (curious) ──────────────────────────────────────
T      = 500
t_demo = np.linspace(0, 1, T)

y_des_discrete = np.vstack([
    np.linspace(0.0, 0.15, T),
    np.zeros(T),
    0.2  * np.sin(np.pi * t_demo),
    -0.3 * t_demo,
    0.1  * np.sin(2 * np.pi * t_demo),
])

dmp_emotion = DMPs_discrete(n_dmps=5, n_bfs=50, dt=0.01)
dmp_emotion.imitate_path(y_des=y_des_discrete)
dmp_emotion.y0   = np.zeros(5)
dmp_emotion.goal = np.array([0.15, 0.0, 0.0, -0.3, 0.1])

# ── 5. Compose: idle + emotion overlay ───────────────────────────────────────
n_steps_total   = dmp_idle.timesteps * N_CYCLES
y_composed      = np.zeros((n_steps_total, 5))
y_emotion_track = np.zeros((n_steps_total, 5))

emotion_start    = dmp_idle.timesteps       # fires after cycle 1
emotion_duration = dmp_emotion.timesteps

dmp_idle.reset_state()
dmp_emotion.reset_state()

emotion_running = False
emotion_step    = 0

for i in range(n_steps_total):
    y_idle_now, _, _ = dmp_idle.step()

    if i == emotion_start:
        dmp_emotion.reset_state()
        emotion_running = True
        emotion_step    = 0
        print(f"\nEmotion triggered at step {i} (t={i*dmp_idle.dt:.2f}s)")

    if emotion_running:
        y_delta, _, _ = dmp_emotion.step()
        emotion_step += 1
        if emotion_step >= emotion_duration:
            emotion_running = False
            print(f"Emotion finished  at step {i} (t={i*dmp_idle.dt:.2f}s)")
    else:
        y_delta = np.zeros(5)

    y_emotion_track[i] = y_delta
    y_composed[i]      = y_idle_now + y_delta

t_composed = np.linspace(0, n_steps_total * dmp_idle.dt, n_steps_total)

print(f"\nEmotion z range  : "
      f"{y_emotion_track[:, 2].min():.4f} to {y_emotion_track[:, 2].max():.4f}")
print(f"Composed z range : "
      f"{y_composed[:, 2].min():.4f} to {y_composed[:, 2].max():.4f}")

# ── 6. Plot — independent y axes per subplot ──────────────────────────────────
axis_names = ['x', 'y', 'z', 'pitch', 'yaw']
plot_axes  = [2, 3]   # z and pitch

# Create subplots with sharex but NOT sharey
fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

for idx in plot_axes:
    axes[0].plot(t_composed, y_idle[:, idx],
                 linewidth=1.5, label=f'{axis_names[idx]}')
axes[0].set_ylabel("Position")
axes[0].set_title("Rhythmic idle alone (4 cycles)")
axes[0].legend()
axes[0].axvline(emotion_start * dmp_idle.dt,
                color='red', linestyle='--', alpha=0.5, label='emotion trigger')

for idx in plot_axes:
    axes[1].plot(t_composed, y_emotion_track[:, idx],
                 linewidth=1.5, label=f'{axis_names[idx]}')
axes[1].set_ylabel("Delta")
axes[1].set_title("Discrete emotion overlay (fires once during cycle 2)")
axes[1].legend()
axes[1].axvline(emotion_start * dmp_idle.dt,
                color='red', linestyle='--', alpha=0.5)

for idx in plot_axes:
    axes[2].plot(t_composed, y_composed[:, idx],
                 linewidth=1.5, label=f'{axis_names[idx]}')
axes[2].set_ylabel("Position")
axes[2].set_title("Composed: idle + emotion overlay")
axes[2].legend()
axes[2].axvline(emotion_start * dmp_idle.dt,
                color='red', linestyle='--', alpha=0.5)
axes[2].set_xlabel("Time (s)")

# Each subplot auto-scales to its own data — no shared y axis
plt.tight_layout()
plt.savefig("lesson_09_output.png", dpi=120)
plt.show()
