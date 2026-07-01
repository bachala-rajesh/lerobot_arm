
# Goal: Save a learned emotion to disk and reload it perfectly.

import numpy as np
import os
import matplotlib.pyplot as plt
from pydmps.dmp_discrete import DMPs_discrete

# ── 1. Helper functions — save and load ───────────────────────────────────────

def save_emotion(filepath, dmp, tau, emotion_name):
    """Save everything needed to reconstruct this emotion."""
    np.savez(
        filepath,
        w          = dmp.w,          # (n_dmps, n_bfs) — the emotion DNA
        y0         = dmp.y0,         # (n_dmps,)
        goal       = dmp.goal,       # (n_dmps,)
        tau        = np.array([tau]),
        n_dmps     = np.array([dmp.n_dmps]),
        n_bfs      = np.array([dmp.n_bfs]),
        dt         = np.array([dmp.dt]),
        name       = np.array([emotion_name])
    )
    
    print(f"Saved '{emotion_name}' → {filepath}.npz")
    

def load_emotion(filepath):
    """Load emotion and reconstruct a ready-to-use DMP."""
    data = np.load(filepath, allow_pickle=True)

    # Reconstruct DMP with same architecture
    dmp = DMPs_discrete(
        n_dmps = int(data['n_dmps'][0]),
        n_bfs  = int(data['n_bfs'][0]),
        dt     = float(data['dt'][0]),
    )

    # Restore learned parameters
    dmp.w    = data['w']
    dmp.y0   = data['y0']
    dmp.goal = data['goal']
    tau      = float(data['tau'][0])
    name     = str(data['name'][0])

    print(f"Loaded '{name}' ← {filepath}")
    return dmp, tau, name


# ── 2. Build an emotion library directory ────────────────────────────────────
EMOTION_DIR = "test_pkg/learn_dmps/emotion_library"
os.makedirs(EMOTION_DIR, exist_ok=True)

T = 500
t = np.linspace(0, 1, T)


# ── 3. Learn and save three emotions ─────────────────────────────────────────

emotions_to_learn = {
    "curious": {
        "y_des": np.vstack([
            np.linspace(0.0, 0.1, T),
            np.zeros(T),
            0.2 * np.sin(np.pi * t),
            -0.3 * t,
            0.1 * np.sin(2 * np.pi * t),
        ]),
        "tau": 1.5,   # curious is medium speed
    },
    "surprised": {
        "y_des": np.vstack([
            np.zeros(T),
            np.zeros(T),
            0.3 * np.sin(np.pi * t)**2,
            0.4 * np.sin(np.pi * t),
            np.zeros(T),
        ]),
        "tau": 0.6,   # surprised is fast
    },
    "sad": {
        "y_des": np.vstack([
            -0.1 * t,
            np.zeros(T),
            -0.15 * t,
            0.3 * t,
            -0.05 * np.sin(np.pi * t),
        ]),
        "tau": 2.5,   # sad is slow
    },
}

learned_dmps = {}
for name, config in emotions_to_learn.items():
    dmp = DMPs_discrete(n_dmps=5, n_bfs=50, dt=0.01)
    dmp.imitate_path(y_des=config["y_des"])

    filepath = os.path.join(EMOTION_DIR, name)
    save_emotion(filepath, dmp, config["tau"], name)
    learned_dmps[name] = (dmp, config["tau"])
    
    

# ── 4. Load them back and verify ─────────────────────────────────────────────
print("\nLoading emotions back from disk...")
loaded_dmps = {}

for name in emotions_to_learn.keys():
    filepath = os.path.join(EMOTION_DIR, f"{name}.npz")
    dmp_loaded, tau, loaded_name = load_emotion(filepath)
    loaded_dmps[name] = (dmp_loaded, tau)

    # Verify weights match exactly
    dmp_original = learned_dmps[name][0]
    max_diff = np.max(np.abs(dmp_loaded.w - dmp_original.w))
    print(f"  '{name}' weight max diff: {max_diff:.2e}")   # should be ~0.0


# ── 5. Rollout loaded emotions and plot ───────────────────────────────────────
print("\nRolling out loaded emotions...")

fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=False)
axis_idx = 2   # plot z axis for all emotions

for ax, (name, (dmp, tau)) in zip(axes, loaded_dmps.items()):
    dmp.reset_state()
    y_track, _, _ = dmp.rollout(tau=tau)

    actual_steps = y_track.shape[0]
    t_plot = np.linspace(0, actual_steps * dmp.dt, actual_steps)

    ax.plot(t_plot, y_track[:, axis_idx],
            color='steelblue', linewidth=2)
    ax.set_ylabel("z position")
    ax.set_title(f"'{name}'  (tau={tau}, duration≈{actual_steps*dmp.dt:.2f}s)")

axes[-1].set_xlabel("Time (s)")
plt.tight_layout()
plt.savefig("lesson_07_output.png", dpi=120)
plt.show()