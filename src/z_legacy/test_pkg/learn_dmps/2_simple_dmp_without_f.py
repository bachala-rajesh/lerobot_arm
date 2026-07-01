"""
Lesson 2: The spring-damper attractor — the heart of every DMP.

We simulate:
    x_ddot = alpha_z * (beta_z * (g - x) - x_dot)

with three demonstrations:
  (1) Critical damping vs underdamped vs overdamped
  (2) Perturbation recovery (push the lamp mid-motion)
  (3) Goal change mid-motion (the lamp 'changes its mind')

For your SO-100 lamp: imagine x is the end-effector height in meters.
"""

import numpy as np
import matplotlib.pyplot as plt


def simulate_spring_damper(
    x0,             # start position
    g,              # goal position
    alpha_z=25.0,   # stiffness-like constant
    beta_z=None,    # if None, use critical damping (alpha_z / 4)
    T=2.0,          # total simulated time [s]
    dt=0.001,       # integration step [s]
    perturbation=None,   # tuple (time, delta_x) to add a kick
    goal_change=None,    # tuple (time, new_goal) to change goal mid-motion
):
    """Simulate a 1D spring-damper attractor with Euler integration."""
    if beta_z is None:
        beta_z = alpha_z / 4.0  # critical damping

    n_steps = int(T / dt)
    t_arr = np.zeros(n_steps)
    x_arr = np.zeros(n_steps)
    xdot_arr = np.zeros(n_steps)

    x = x0
    xdot = 0.0
    g_current = g

    for i in range(n_steps):
        t = i * dt

        # Apply perturbation if scheduled
        if perturbation is not None and abs(t - perturbation[0]) < dt / 2:
            x += perturbation[1]   # instantaneous position kick

        # Apply goal change if scheduled
        if goal_change is not None and t >= goal_change[0]:
            g_current = goal_change[1]

        # The DMP attractor equation:
        xddot = alpha_z * (beta_z * (g_current - x) - xdot)

        # Euler integration
        xdot += xddot * dt
        x    += xdot  * dt

        t_arr[i] = t
        x_arr[i] = x
        xdot_arr[i] = xdot

    return t_arr, x_arr, xdot_arr


# ============================================================
# Experiment 1: damping comparison
# ============================================================
alpha = 25.0
crit_beta = alpha / 4.0  # = 6.25

t_under, x_under, _   = simulate_spring_damper(0, 1.0, alpha_z=alpha, beta_z=1.0)        # underdamped
t_crit,  x_crit,  _   = simulate_spring_damper(0, 1.0, alpha_z=alpha, beta_z=crit_beta)  # critical
t_over,  x_over,  _   = simulate_spring_damper(0, 1.0, alpha_z=alpha, beta_z=20.0)       # overdamped

# ============================================================
# Experiment 2: perturbation recovery
# ============================================================
t_p, x_p, _ = simulate_spring_damper(
    0, 1.0, alpha_z=alpha, beta_z=crit_beta,
    perturbation=(0.5, -0.4),  # at t=0.5s, lamp is shoved DOWN by 0.4m
)

# ============================================================
# Experiment 3: goal change mid-motion
# ============================================================
t_g, x_g, _ = simulate_spring_damper(
    0, 1.0, alpha_z=alpha, beta_z=crit_beta, T=3.0,
    goal_change=(1.0, 1.5),   # at t=1.0s, change goal from 1.0 to 1.5
)

# ============================================================
# Plot
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

axes[0].plot(t_under, x_under, label='underdamped (β=1)', lw=2)
axes[0].plot(t_crit,  x_crit,  label=f'critical (β={crit_beta})', lw=2)
axes[0].plot(t_over,  x_over,  label='overdamped (β=20)', lw=2)
axes[0].axhline(1.0, color='gray', ls='--', alpha=0.5)
axes[0].set_title("Damping comparison\n(α_z=25 fixed)")
axes[0].set_xlabel("time [s]"); axes[0].set_ylabel("x [m]")
axes[0].legend()

axes[1].plot(t_p, x_p, lw=2, color='C2')
axes[1].axhline(1.0, color='gray', ls='--', alpha=0.5, label='goal')
axes[1].axvline(0.5, color='red', ls=':', alpha=0.7, label='shove!')
axes[1].set_title("Perturbation recovery\n(critically damped, kicked at t=0.5s)")
axes[1].set_xlabel("time [s]"); axes[1].set_ylabel("x [m]")
axes[1].legend()

axes[2].plot(t_g, x_g, lw=2, color='C3')
axes[2].axhline(1.0, color='gray', ls='--', alpha=0.4, label='original goal')
axes[2].axhline(1.5, color='black', ls='--', alpha=0.6, label='new goal')
axes[2].axvline(1.0, color='red', ls=':', alpha=0.7, label='goal change')
axes[2].set_title("Goal change mid-motion\n(no replanning needed!)")
axes[2].set_xlabel("time [s]"); axes[2].set_ylabel("x [m]")
axes[2].legend()

plt.tight_layout()
plt.show()
print()
print("Observations:")
print(f"  Critical damping (β=α/4={crit_beta}) gives smoothest goal-reaching.")
print(f"  Underdamped overshoots and oscillates — NOT what we want from the attractor.")
print(f"  Overdamped is slow and never quite arrives in 2s.")
print(f"  Perturbation: lamp shoved down 0.4m at t=0.5, recovers smoothly to goal.")
print(f"  Goal change: at t=1.0 goal jumps to 1.5 — trajectory just smoothly redirects.")