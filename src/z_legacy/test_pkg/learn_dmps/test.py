"""
Lesson 1: Why polynomial trajectories are not enough.

We will generate a quintic (5th-order) polynomial trajectory from a
start point to a goal point. This is a very common "smooth interpolation"
in robotics. We will then see what it cannot do.

Think of x(t) here as the height of your lamp's end-effector.
"""

import numpy as np
import matplotlib.pyplot as plt


def quintic_polynomial(x0, xg, T, n_points=200):
    """
    Quintic polynomial from x0 to xg over duration T,
    with zero velocity and zero acceleration at both ends.
    This is the "smoothest" basic interpolation.
    """
    t = np.linspace(0, T, n_points)
    s = t / T  # normalized time, 0 to 1
    # Quintic with zero vel/accel at endpoints:
    # x(s) = x0 + (xg - x0) * (10 s^3 - 15 s^4 + 6 s^5)
    shape = 10 * s**3 - 15 * s**4 + 6 * s**5
    x = x0 + (xg - x0) * shape
    return t, x


# --- Scenario A: a normal motion ---
t, x = quintic_polynomial(x0=0.0, xg=1.0, T=2.0)

# --- Scenario B: same motion, but the goal changes halfway ---
# Naive approach: re-plan a NEW polynomial from current state to new goal
t1, x1 = quintic_polynomial(x0=0.0, xg=1.0, T=2.0)
half = len(t1) // 2
# at t=1.0 we are at x1[half]. Suppose new goal is 1.5
t2, x2 = quintic_polynomial(x0=x1[half], xg=1.5, T=1.0)
t_combined = np.concatenate([t1[:half], t2 + t1[half]])
x_combined = np.concatenate([x1[:half], x2])

# --- Scenario C: a "personality" shape we want — overshoot + settle ---
# This is what "curious" might look like. Pure polynomial cannot do this
# while also guaranteeing it ends at the goal with zero velocity.
t3 = np.linspace(0, 2, 200)
x3_desired = 1.0 * (1 - np.exp(-3 * t3)) * (1 + 0.15 * np.sin(4 * t3))  # decaying oscillation

# Plot all three
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].plot(t, x, lw=2)
axes[0].axhline(1.0, color='gray', ls='--', alpha=0.5, label='goal')
axes[0].set_title("A: Quintic, fixed goal\n(works fine)")
axes[0].set_xlabel("time [s]"); axes[0].set_ylabel("x [m]")
axes[0].legend()

axes[1].plot(t_combined, x_combined, lw=2, label='replanned')
axes[1].axvline(1.0, color='red', ls=':', alpha=0.7, label='goal change')
axes[1].axhline(1.5, color='gray', ls='--', alpha=0.5, label='new goal')
axes[1].set_title("B: Goal changes mid-motion\n(notice the kink — replan needed)")
axes[1].set_xlabel("time [s]"); axes[1].set_ylabel("x [m]")
axes[1].legend()

axes[2].plot(t3, x3_desired, lw=2, color='purple')
axes[2].axhline(1.0, color='gray', ls='--', alpha=0.5, label='goal')
axes[2].set_title("C: Expressive 'curious' shape\n(polynomial cannot produce this AND guarantee goal)")
axes[2].set_xlabel("time [s]"); axes[2].set_ylabel("x [m]")
axes[2].legend()

plt.tight_layout()
plt.savefig('/home/mira/workspaces/lerobot_ws/src/test_pkg/learn_dmps/lesson1_output.png', dpi=80)
print("Saved lesson1_output.png")
print()
print("Observations:")
print("- Scenario A: polynomial works, but it's a fixed shape — no personality.")
print("- Scenario B: when goal changes, you must re-plan. Velocity may be discontinuous.")
print("- Scenario C: expressive shapes need a way to inject 'shape' on top of attraction to goal.")