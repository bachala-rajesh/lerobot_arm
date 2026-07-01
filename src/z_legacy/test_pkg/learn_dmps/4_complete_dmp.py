"""
Lesson 4: A complete DMP from scratch.

We implement everything we've learned:
  - Transformation system (spring-damper attractor)
  - Canonical system (phase variable)
  - Forcing function (weighted sum of Gaussian basis functions)

Then we vary the weights and watch personality emerge.
"""

import numpy as np
import matplotlib.pyplot as plt


class SimpleDMP:
    """
    A 1D Dynamic Movement Primitive, built from scratch.

    Equations:
        s_dot = -alpha_s * s                              (canonical)
        x_ddot = alpha_z * (beta_z * (g - x) - x_dot) + f(s)
        f(s) = s * sum(w_i * psi_i(s)) / sum(psi_i(s))
        psi_i(s) = exp(-h_i * (s - c_i)^2)
    """

    def __init__(self, n_bfs=10, alpha_z=25.0, alpha_s=4.0, T=1.0):
        self.n_bfs = n_bfs
        self.alpha_z = alpha_z
        self.beta_z = alpha_z / 4.0      # critical damping
        self.alpha_s = alpha_s
        self.T = T

        # Place basis function centers evenly in PHASE space (not time).
        # Phase decays from 1 to 0, so we want centers in (0, 1].
        # We space them evenly in time and convert to phase via s = exp(-alpha_s * t):
        t_centers = np.linspace(0, T, n_bfs)
        self.c = np.exp(-alpha_s * t_centers)            # centers in phase space

        # Choose widths so adjacent Gaussians overlap smoothly.
        # A common heuristic:
        self.h = 1.0 / (np.diff(self.c)**2)
        self.h = np.append(self.h, self.h[-1])           # match length

        # Weights — start at zero (= no forcing = pure attractor)
        self.w = np.zeros(n_bfs)

    def basis_functions(self, s):
        """Evaluate all psi_i at phase s. Returns shape (n_bfs,)."""
        return np.exp(-self.h * (s - self.c)**2)

    def forcing(self, s):
        """f(s) — the weighted, normalized, phase-multiplied forcing."""
        psi = self.basis_functions(s)
        # Normalized weighted sum, multiplied by s
        return s * np.dot(self.w, psi) / (np.sum(psi) + 1e-10)

    def rollout(self, x0, g, dt=0.001):
        """Integrate the DMP from x0 to goal g and return the trajectory."""
        n_steps = int(self.T / dt)
        t_arr = np.zeros(n_steps)
        x_arr = np.zeros(n_steps)
        s_arr = np.zeros(n_steps)
        f_arr = np.zeros(n_steps)

        x = x0
        x_dot = 0.0
        s = 1.0

        for i in range(n_steps):
            f = self.forcing(s)
            x_ddot = self.alpha_z * (self.beta_z * (g - x) - x_dot) + f

            # Euler integration
            x_dot += x_ddot * dt
            x     += x_dot  * dt
            s     += -self.alpha_s * s * dt

            t_arr[i] = i * dt
            x_arr[i] = x
            s_arr[i] = s
            f_arr[i] = f

        return t_arr, x_arr, s_arr, f_arr


# ============================================================
# Experiment: zero weights vs. handcrafted personality weights
# ============================================================

# Common settings
x0, g = 0.0, 1.0
T = 2.0

# DMP with zero weights — should look exactly like Lesson 2's attractor
dmp_neutral = SimpleDMP(n_bfs=10, alpha_z=25.0, alpha_s=4.0, T=T)
t_n, x_n, s_n, f_n = dmp_neutral.rollout(x0, g)

# DMP with weights that produce an "overshoot then settle" — a CURIOUS feel.
# We'll push positively in the middle of the motion (a leaning-in bump).
dmp_curious = SimpleDMP(n_bfs=10, alpha_z=25.0, alpha_s=4.0, T=T)
dmp_curious.w = np.array([0, 50, 100, 150, 100, 50, -50, -100, -50, 0], dtype=float)
t_c, x_c, s_c, f_c = dmp_curious.rollout(x0, g)

# DMP with weights that pull DOWN early — a HESITANT/SAD feel.
# Lamp dips slightly before rising to goal, like reluctance.
dmp_sad = SimpleDMP(n_bfs=10, alpha_z=25.0, alpha_s=4.0, T=T)
dmp_sad.w = np.array([-100, -200, -150, -50, 0, 50, 0, 0, 0, 0], dtype=float)
t_s, x_s, s_s, f_s = dmp_sad.rollout(x0, g)

# DMP with weights that wobble — a SURPRISED/oscillating feel.
dmp_surprised = SimpleDMP(n_bfs=10, alpha_z=25.0, alpha_s=4.0, T=T)
dmp_surprised.w = np.array([200, -200, 200, -200, 200, -200, 100, -100, 50, 0], dtype=float)
t_q, x_q, s_q, f_q = dmp_surprised.rollout(x0, g)


# ============================================================
# Plot
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 9))

# Top-left: trajectories
ax = axes[0, 0]
ax.plot(t_n, x_n, lw=2, label='neutral (w=0)')
ax.plot(t_c, x_c, lw=2, label='curious (lean-in)')
ax.plot(t_s, x_s, lw=2, label='sad (hesitate)')
ax.plot(t_q, x_q, lw=2, label='surprised (wobble)')
ax.axhline(g, color='gray', ls='--', alpha=0.5)
ax.set_title("Trajectories x(t)\n(all start at 0, all reach goal=1)")
ax.set_xlabel("time [s]"); ax.set_ylabel("x [m]")
ax.legend()
ax.grid(True, alpha=0.3)

# Top-right: forcing functions over time
ax = axes[0, 1]
ax.plot(t_n, f_n, lw=2, label='neutral')
ax.plot(t_c, f_c, lw=2, label='curious')
ax.plot(t_s, f_s, lw=2, label='sad')
ax.plot(t_q, f_q, lw=2, label='surprised')
ax.axhline(0, color='gray', ls='-', alpha=0.4)
ax.set_title("Forcing f(s(t))\n(notice how all fade to 0 at the end)")
ax.set_xlabel("time [s]"); ax.set_ylabel("f")
ax.legend()
ax.grid(True, alpha=0.3)

# Bottom-left: basis functions in phase space
ax = axes[1, 0]
s_grid = np.linspace(1, 0, 300)
psi_grid = np.array([dmp_neutral.basis_functions(s) for s in s_grid])  # shape (300, n_bfs)
for i in range(dmp_neutral.n_bfs):
    ax.plot(s_grid, psi_grid[:, i], lw=1.5, alpha=0.7)
ax.set_title("Basis functions ψ_i(s)\n(10 Gaussian bumps along phase axis)")
ax.set_xlabel("phase s"); ax.set_ylabel("ψ")
ax.invert_xaxis()  # phase goes 1 → 0, so motion progresses left-to-right
ax.grid(True, alpha=0.3)

# Bottom-right: weights as bar chart
ax = axes[1, 1]
indices = np.arange(dmp_neutral.n_bfs)
width = 0.2
ax.bar(indices - 1.5*width, dmp_neutral.w,   width, label='neutral')
ax.bar(indices - 0.5*width, dmp_curious.w,   width, label='curious')
ax.bar(indices + 0.5*width, dmp_sad.w,       width, label='sad')
ax.bar(indices + 1.5*width, dmp_surprised.w, width, label='surprised')
ax.axhline(0, color='gray', alpha=0.5)
ax.set_title("Weights w_i\n(personality lives in this vector)")
ax.set_xlabel("basis index i"); ax.set_ylabel("weight")
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print()
print("Observations:")
print("  Top-left: four DIFFERENT motions, all starting at 0 and ending at 1.")
print("            The 'shape' between start and goal is the personality.")
print("  Top-right: every forcing curve fades to zero at the end — this is the")
print("             's-multiplier' guaranteeing goal convergence regardless of weights.")
print("  Bottom-left: 10 bumps along phase. At any s, only 1-2 bumps are active.")
print("  Bottom-right: emotion = weight vector. This is what we'll LEARN in Lesson 5.")