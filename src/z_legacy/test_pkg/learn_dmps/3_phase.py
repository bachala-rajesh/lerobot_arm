"""
Lesson 3: The phase variable (canonical system).

The phase s(t) is an internal "motion progress clock" that:
  - Starts at 1 when the motion begins
  - Decays smoothly toward 0 as the motion progresses
  - Replaces wall-clock time as the input to the forcing function

Equation:    s_dot = -alpha_s * s,   s(0) = 1
Analytical:  s(t) = exp(-alpha_s * t)

We will:
  1) Plot s(t) for several alpha_s values and see how it behaves.
  2) Plot s vs an arbitrary "personality bump" to show how the bump
     gets stretched/compressed when alpha_s changes — i.e., the shape
     is preserved, only the duration changes.
"""

import numpy as np
import matplotlib.pyplot as plt


def simulate_canonical(alpha_s, T=2.0, dt=0.001):
    """Integrate s_dot = -alpha_s * s from s(0)=1."""
    n_steps = int(T / dt)
    t_arr = np.zeros(n_steps)
    s_arr = np.zeros(n_steps)
    s = 1.0
    for i in range(n_steps):
        t = i * dt
        s_dot = -alpha_s * s
        s += s_dot * dt
        t_arr[i] = t
        s_arr[i] = s
    return t_arr, s_arr


# ============================================================
# Experiment 1: how alpha_s shapes the phase
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

for alpha_s in [1.0, 2.0, 4.0, 8.0]:
    t, s = simulate_canonical(alpha_s, T=2.0)
    axes[0].plot(t, s, lw=2, label=f"α_s = {alpha_s}")

axes[0].set_title("Phase s(t) for different α_s\n(higher α_s → faster decay → faster motion)")
axes[0].set_xlabel("real time t [s]")
axes[0].set_ylabel("phase s")
axes[0].axhline(0, color='gray', ls='--', alpha=0.4)
axes[0].axhline(1, color='gray', ls='--', alpha=0.4)
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# ============================================================
# Experiment 2: a "personality bump" defined as a function of s
#
# Imagine f(s) = some shape. Here we use a Gaussian centered at s=0.5
# (i.e., halfway through the motion in *phase* terms).
# When we plot f(s(t)) for different alpha_s, the bump gets stretched
# along the time axis — but its shape vs phase is identical.
# ============================================================

def personality_bump(s):
    """A 'curious peek up' bump, centered halfway through the motion."""
    return np.exp(-30 * (s - 0.5)**2)

# Plot the bump in phase domain (this is the 'design space')
s_grid = np.linspace(1, 0, 200)   # phase decreases from 1 to 0
axes[1].plot(s_grid, personality_bump(s_grid), lw=2, color='purple')
axes[1].set_title("The 'personality bump' f(s)\n(designed in phase space — shape is fixed)")
axes[1].set_xlabel("phase s  (1 = start, 0 = end)")
axes[1].set_ylabel("f(s)")
axes[1].invert_xaxis()  # so motion progresses left-to-right in this plot
axes[1].grid(True, alpha=0.3)

# Now show the same bump played out over time, for different alpha_s
for alpha_s in [1.0, 2.0, 4.0, 8.0]:
    t, s = simulate_canonical(alpha_s, T=4.0)
    axes[2].plot(t, personality_bump(s), lw=2, label=f"α_s = {alpha_s}")

axes[2].set_title("Same bump f(s(t)) playing in real time\n(α_s controls how long the motion lasts)")
axes[2].set_xlabel("real time t [s]")
axes[2].set_ylabel("f(s(t))")
axes[2].legend()
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print()
print("Observations:")
print("  Plot 1: Higher α_s makes s decay faster — the 'motion clock' ticks faster.")
print("  Plot 2: We design the personality in phase space (a fixed shape).")
print("  Plot 3: The SAME shape plays out over different real durations,")
print("          purely by changing α_s. No re-designing the bump.")
print()
print("This is wishlist item #4 (time-flexible). For your lamp, this means:")
print("  curious_dmp.alpha_s = 4   --> 1-second curious motion")
print("  curious_dmp.alpha_s = 1   --> 4-second pensive curious motion")
print("  Same shape. Same emotion. Different speeds.")