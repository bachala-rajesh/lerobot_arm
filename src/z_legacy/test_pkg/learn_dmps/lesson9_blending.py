# Goal: Blend two emotions at varying ratios and observe interpolation.

import numpy as np
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# ── 1. Learn two emotions ─────────────────────────────────────────────────────
T = 500
t = np.linspace(0, 1, T)

# Emotion A — "curious": leans forward, tilts head
config_A = {
    "y_des": np.vstack([
        np.linspace(0.0,  0.15, T),
        np.zeros(T),
        0.2  * np.sin(np.pi * t),
        -0.3 * t,
        0.1  * np.sin(2 * np.pi * t),
    ]),
    "y0"  : np.array([0.0,  0.0, 0.0,  0.0,  0.0]),
    "goal": np.array([0.15, 0.0, 0.0, -0.3,  0.1]),
    "tau" : 1.5,
}



# Emotion B — "sad": droops down, slow
config_B = {
    "y_des": np.vstack([
        -0.1 * t,
        np.zeros(T),
        -0.15 * t,
        0.3  * t,
        -0.05 * np.sin(np.pi * t),
    ]),
    "y0"  : np.array([0.0,  0.0,  0.0, 0.0,  0.0]),
    "goal": np.array([-0.1, 0.0, -0.15, 0.3, -0.05]),
    "tau" : 2.5,
}


def learn_emotion(config):
    dmp = DMPs_discrete(n_dmps=5, n_bfs=50, dt=0.01)
    dmp.imitate_path(y_des=config["y_des"])
    dmp.y0   = config["y0"]
    dmp.goal = config["goal"]
    return dmp

dmp_A = learn_emotion(config_A)
dmp_B = learn_emotion(config_B)

print("Learned emotions A (curious) and B (sad)")
print(f"  A weights shape: {dmp_A.w.shape}")
print(f"  B weights shape: {dmp_B.w.shape}")


# ── 2. Blend at five ratios ───────────────────────────────────────────────────
# alpha=1.0 → pure A, alpha=0.0 → pure B
alphas = [1.0, 0.75, 0.5, 0.25, 0.0]
colors = ['steelblue', 'cornflowerblue', 'mediumpurple', 'salmon', 'red']
labels = [
    'pure curious (α=1.0)',
    'mostly curious (α=0.75)',
    'blend 50/50 (α=0.5)',
    'mostly sad (α=0.25)',
    'pure sad (α=0.0)',
]


# We need one DMP to run blended weights through
dmp_blend = DMPs_discrete(n_dmps=5, n_bfs=50, dt=0.01)

results = []

for alpha in alphas:
    # Blend weights
    dmp_blend.w    = alpha * dmp_A.w    + (1 - alpha) * dmp_B.w

    # Blend y0, goal, tau
    dmp_blend.y0   = alpha * dmp_A.y0   + (1 - alpha) * dmp_B.y0
    dmp_blend.goal = alpha * dmp_A.goal + (1 - alpha) * dmp_B.goal
    tau_blend      = alpha * config_A['tau'] + (1 - alpha) * config_B['tau']

    dmp_blend.reset_state()
    y_track, _, _ = dmp_blend.rollout(tau=tau_blend)

    actual_steps = y_track.shape[0]
    t_plot = np.linspace(0, actual_steps * dmp_blend.dt, actual_steps)
    results.append((t_plot, y_track, tau_blend))




# ── 3. Print blend parameters ─────────────────────────────────────────────────
print("\nBlend parameters at each alpha:")
print(f"  {'alpha':<8} {'tau':<8} {'goal_z':<10} {'goal_pitch'}")
print("  " + "-" * 40)
for alpha, (_, y_track, tau_blend) in zip(alphas, results):
    goal_blend = alpha * dmp_A.goal + (1 - alpha) * dmp_B.goal
    print(f"  {alpha:<8.2f} {tau_blend:<8.3f} "
          f"{goal_blend[2]:<10.4f} {goal_blend[3]:.4f}")

# ── 4. Plot z axis — shape interpolation ─────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(10, 8))

for (t_plot, y_track, tau_blend), color, label in \
        zip(results, colors, labels):
    axes[0].plot(t_plot, y_track[:, 2],
                 color=color, linewidth=2, label=label)

axes[0].set_ylabel("z position")
axes[0].set_title("Emotion blending — z axis (shape interpolation)")
axes[0].legend(fontsize=8)
axes[0].set_xlabel("Time (s)")

# ── 5. Plot pitch axis — shape interpolation ──────────────────────────────────
for (t_plot, y_track, tau_blend), color, label in \
        zip(results, colors, labels):
    axes[1].plot(t_plot, y_track[:, 3],
                 color=color, linewidth=2, label=label)

axes[1].set_ylabel("pitch")
axes[1].set_title("Emotion blending — pitch axis")
axes[1].legend(fontsize=8)
axes[1].set_xlabel("Time (s)")

plt.tight_layout()
plt.savefig("lesson_08_blending.png", dpi=120)
plt.show()
