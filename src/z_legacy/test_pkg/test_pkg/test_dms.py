"""
DMP Single Joint Explorer
=========================
Learn Dynamic Movement Primitives hands-on, one joint at a time.

Usage:
    python dmp_explorer.py --demo basic
    python dmp_explorer.py --demo goal_change
    python dmp_explorer.py --demo perturb
    python dmp_explorer.py --demo no_shake
    python dmp_explorer.py --demo surprised
    python dmp_explorer.py --demo all

Install dependencies first:
    pip install numpy matplotlib pydmps
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

try:
    import pydmps
    import pydmps.dmp_discrete
except ImportError:
    print("ERROR: pydmps not installed.")
    print("Run: pip install pydmps")
    exit(1)


# ─────────────────────────────────────────────
# Core DMP wrapper — thin layer over pydmps
# ─────────────────────────────────────────────

class SingleJointDMP:
    """
    Wraps pydmps for a single joint angle (degrees).
    
    Parameters
    ----------
    n_bfs : int
        Number of Gaussian basis functions.
        More = more expressive forcing function.
        Start with 10-20. Use 50+ when learning from demonstration.
    alpha : float
        Spring stiffness. Higher = faster convergence to goal.
        Typical range: 10-50.
    beta : float
        Set automatically as alpha/4 for critical damping baseline.
        Override to tune damping behaviour.
    """

    def __init__(self, n_bfs=20, alpha=25.0):
        beta = alpha / 4.0
        self.dmp = pydmps.dmp_discrete.DMPs_discrete(
            n_dmps=1,
            n_bfs=n_bfs,
            ay=np.array([alpha]),
            by=np.array([beta]),
        )
        self.alpha = alpha
        self.n_bfs = n_bfs

    def learn_from_demo(self, trajectory_deg):
        """
        Learn forcing function weights from a demonstrated trajectory.
        trajectory_deg: 1D array of joint angles in degrees.
        """
        traj = np.array(trajectory_deg, dtype=float).reshape(1, -1)
        self.dmp.imitate_path(y_des=traj)
        print(f"  Learned {self.n_bfs} weights from {len(trajectory_deg)}-point demo")

    def rollout(self, start_deg, goal_deg, duration=2.0, dt=0.01,
                goal_change=None, perturb=None):
        """
        Run DMP from start to goal.

        Parameters
        ----------
        start_deg : float   Starting joint angle in degrees.
        goal_deg  : float   Target joint angle in degrees.
        duration  : float   Motion duration in seconds.
        dt        : float   Timestep.
        goal_change : tuple (time_sec, new_goal_deg) — change goal mid-motion.
        perturb   : tuple   (time_sec, magnitude_deg) — push joint off course.

        Returns
        -------
        t, y, dy, forcing  — time, position, velocity, forcing function arrays
        """
        self.dmp.y0 = np.array([start_deg])
        self.dmp.goal = np.array([goal_deg])
        self.dmp.reset_state()

        steps = int(duration / dt)
        t_arr, y_arr, dy_arr, f_arr = [], [], [], []

        y  = np.array([start_deg], dtype=float)
        dy = np.array([0.0])

        for i in range(steps):
            t = i * dt

            # optional: change goal mid-motion
            if goal_change and abs(t - goal_change[0]) < dt * 1.5:
                self.dmp.goal = np.array([goal_change[1]])
                print(f"  [t={t:.2f}s] Goal changed → {goal_change[1]:.1f}°")

            # optional: perturb (push joint off course)
            if perturb and abs(t - perturb[0]) < dt * 1.5:
                y += perturb[1]
                print(f"  [t={t:.2f}s] Perturbation applied: {perturb[1]:+.1f}°")

            y_new, dy_new, _ = self.dmp.step(external_force=None)

            # manually inject current y if perturbed
            self.dmp.y = y
            self.dmp.dy = dy

            y_new, dy_new, _ = self.dmp.step()
            y  = y_new.copy()
            dy = dy_new.copy()

            # compute forcing function value for visualisation
            s = self.dmp.cs.step()
            psi = np.exp(-self.dmp.h * (s - self.dmp.c) ** 2)
            f = (np.dot(psi, self.dmp.w[0]) / (psi.sum() + 1e-10)
                 * s * (goal_deg - start_deg))

            t_arr.append(t)
            y_arr.append(float(y[0]))
            dy_arr.append(float(dy[0]))
            f_arr.append(float(f))

        return (np.array(t_arr), np.array(y_arr),
                np.array(dy_arr), np.array(f_arr))


# ─────────────────────────────────────────────
# Plotting helper
# ─────────────────────────────────────────────

def plot_result(t, y, dy, f, title, goal_deg,
                goal_change=None, perturb_t=None,
                notes=""):
    fig = plt.figure(figsize=(11, 7))
    fig.suptitle(title, fontsize=13, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(3, 1, hspace=0.45)

    # — Position
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(t, y, color='#534AB7', linewidth=2, label='joint angle (°)')
    ax1.axhline(goal_deg, color='#1D9E75', linewidth=1.2,
                linestyle='--', label=f'goal = {goal_deg:.0f}°')
    if goal_change:
        ax1.axvline(goal_change[0], color='#D85A30', linewidth=1,
                    linestyle=':', label=f'goal → {goal_change[1]:.0f}° at t={goal_change[0]}s')
        ax1.axhline(goal_change[1], color='#D85A30', linewidth=1,
                    linestyle='--', alpha=0.6)
    if perturb_t:
        ax1.axvline(perturb_t, color='#E24B4A', linewidth=1.5,
                    linestyle=':', label=f'perturbation at t={perturb_t}s')
    ax1.set_ylabel('angle (°)', fontsize=10)
    ax1.set_title('joint position', fontsize=10)
    ax1.legend(fontsize=9, loc='upper right')
    ax1.grid(True, alpha=0.2)

    # — Velocity
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(t, dy, color='#1D9E75', linewidth=1.5)
    ax2.axhline(0, color='gray', linewidth=0.5)
    ax2.set_ylabel('velocity (°/s)', fontsize=10)
    ax2.set_title('joint velocity', fontsize=10)
    ax2.grid(True, alpha=0.2)

    # — Forcing function
    ax3 = fig.add_subplot(gs[2])
    ax3.fill_between(t, f, alpha=0.3, color='#D85A30')
    ax3.plot(t, f, color='#D85A30', linewidth=1.5)
    ax3.axhline(0, color='gray', linewidth=0.5)
    ax3.set_ylabel('forcing f(s)', fontsize=10)
    ax3.set_xlabel('time (s)', fontsize=10)
    ax3.set_title('forcing function — this is what creates personality', fontsize=10)
    ax3.grid(True, alpha=0.2)

    if notes:
        fig.text(0.02, 0.01, notes, fontsize=8.5,
                 color='#5F5E5A', wrap=True,
                 verticalalignment='bottom')

    plt.savefig(f"{title.replace(' ', '_').lower()}.png",
                dpi=130, bbox_inches='tight')
    print(f"  Saved: {title.replace(' ', '_').lower()}.png")
    plt.show()


# ─────────────────────────────────────────────
# Demo functions — one per concept
# ─────────────────────────────────────────────

def demo_basic():
    """
    CONCEPT: Basic DMP — smooth point-to-point motion.
    
    The lamp joint moves from 0° to 45° smoothly.
    Watch how position, velocity, and forcing function relate.
    
    Key observations:
    - Velocity is zero at start and end (smooth)
    - Forcing function is zero at the end (guaranteed arrival)
    - Change alpha to make it faster/slower
    """
    print("\n── Demo: Basic point-to-point ──")
    print("Joint moves 0° → 45°. Smooth arrival guaranteed by spring.")

    dmp = SingleJointDMP(n_bfs=20, alpha=25)

    # zero forcing weights = pure spring-damper (like your polynomial)
    dmp.dmp.w = np.zeros_like(dmp.dmp.w)

    t, y, dy, f = dmp.rollout(start_deg=0, goal_deg=45, duration=2.0)

    plot_result(t, y, dy, f,
        title="Basic DMP — zero forcing",
        goal_deg=45,
        notes="Zero forcing weights = pure spring-damper. Similar to your quintic polynomial. "
              "Try changing alpha (stiffness) to see faster/slower response.")


def demo_goal_change():
    """
    CONCEPT: Goal changes mid-motion — DMP adapts automatically.
    
    This is impossible with a pre-planned polynomial.
    The lamp starts moving toward 45°, then at t=1.0s the target
    moves to 70°. The DMP smoothly redirects — no recomputation.
    
    Real use case: lamp is tracking a moving attention point.
    """
    print("\n── Demo: Goal change mid-motion ──")
    print("Starts toward 45°. At t=1.0s goal changes to 70°.")
    print("Watch the trajectory redirect smoothly — no replan needed.")

    dmp = SingleJointDMP(n_bfs=20, alpha=25)
    dmp.dmp.w = np.zeros_like(dmp.dmp.w)

    t, y, dy, f = dmp.rollout(
        start_deg=0,
        goal_deg=45,
        duration=3.0,
        goal_change=(1.0, 70)   # at t=1.0s, new goal = 70°
    )

    plot_result(t, y, dy, f,
        title="DMP — Goal changes mid-motion",
        goal_deg=45,
        goal_change=(1.0, 70),
        notes="At t=1.0s goal shifts from 45° to 70°. DMP redirects continuously. "
              "A polynomial trajectory would need full recomputation from current state.")


def demo_perturb():
    """
    CONCEPT: Perturbation recovery.
    
    At t=1.0s something pushes the joint 20° off course.
    The spring attractor pulls it back automatically.
    No replanning. No explicit recovery logic.
    
    Real use case: someone bumps the lamp while it is moving.
    """
    print("\n── Demo: Perturbation recovery ──")
    print("At t=1.0s joint is pushed +20° off course.")
    print("Spring attractor pulls it back. Goal still reached cleanly.")

    dmp = SingleJointDMP(n_bfs=20, alpha=25)
    dmp.dmp.w = np.zeros_like(dmp.dmp.w)

    t, y, dy, f = dmp.rollout(
        start_deg=0,
        goal_deg=45,
        duration=3.0,
        perturb=(1.0, 20.0)     # at t=1.0s, push +20°
    )

    plot_result(t, y, dy, f,
        title="DMP — Perturbation recovery",
        goal_deg=45,
        perturb_t=1.0,
        notes="Perturbation at t=1.0s pushes joint 20° off course. "
              "Spring attractor recovers automatically. No replanning needed.")


def demo_no_shake():
    """
    CONCEPT: Oscillatory motion via forcing function weights.
    
    By shaping the forcing function with alternating weights,
    the joint oscillates before settling — head shake 'no'.
    
    The forcing function decays with the phase variable s,
    so oscillation naturally fades as the motion completes.
    Always arrives at goal cleanly.
    
    Key insight: you do NOT hand-code oscillation.
    The weights encode the shape. The spring guarantees arrival.
    """
    print("\n── Demo: Head shake 'no' via forcing weights ──")
    print("Forcing function creates oscillation that fades naturally.")
    print("Always arrives at goal — spring guarantees it.")

    dmp = SingleJointDMP(n_bfs=20, alpha=30)

    # manually set weights to create oscillation
    # alternating signs = back-and-forth motion
    w = np.zeros((1, 20))
    w[0, :] = [
         50, -50,  45, -40,  35,
        -30,  25, -20,  15, -10,
          8,  -6,   4,  -3,   2,
         -1,   1,  -1,   0,   0
    ]
    dmp.dmp.w = w

    t, y, dy, f = dmp.rollout(start_deg=0, goal_deg=5, duration=2.5)

    plot_result(t, y, dy, f,
        title="DMP — Head shake no (oscillatory forcing)",
        goal_deg=5,
        notes="Alternating forcing weights create oscillation. "
              "Forcing decays with phase s → oscillation fades naturally. "
              "Goal is only 5° — the shake is entirely from the forcing function.")


def demo_surprised():
    """
    CONCEPT: Surprised recoil — fast initial move away from goal,
    then snappy return with overshoot and bounce.
    
    Achieved by:
    - Strong negative forcing weight at start (pushes away)  
    - Low damping (alpha/beta ratio → underdamped)
    - High stiffness (snappy return)
    
    The lamp recoils, overshoots, rings down — physically natural.
    """
    print("\n── Demo: Surprised recoil ──")
    print("Strong negative forcing + low damping = recoil + bounce.")
    print("Watch position go negative before snapping to goal.")

    # low beta = underdamped = bouncy
    dmp = SingleJointDMP(n_bfs=20, alpha=40)
    dmp.dmp.by = np.array([3.0])   # override beta: lower = more bounce

    w = np.zeros((1, 20))
    w[0, :] = [
        -80, -40,  20,  10,   5,
          3,   2,   1,   0,   0,
          0,   0,   0,   0,   0,
          0,   0,   0,   0,   0
    ]
    dmp.dmp.w = w

    t, y, dy, f = dmp.rollout(start_deg=0, goal_deg=30, duration=2.0)

    plot_result(t, y, dy, f,
        title="DMP — Surprised recoil",
        goal_deg=30,
        notes="Negative initial forcing pushes joint away from goal (recoil). "
              "Low beta (underdamped) causes overshoot and ring-down on arrival. "
              "Tune beta: lower = bouncier, higher = stiffer settle.")


def demo_learn_from_demo():
    """
    CONCEPT: Learn DMP weights from a hand-crafted demonstration.
    
    You provide a trajectory (as if from teleoperation).
    DMP learns the weights automatically.
    Then you replay it to a NEW goal — shape is preserved,
    start/end adapts automatically.
    
    This is how you will use LeRobot teleoperation later.
    """
    print("\n── Demo: Learn from demonstration ──")
    print("Creates a 'curious lean' trajectory manually.")
    print("DMP learns weights. Replays to different goal automatically.")

    # craft a demonstration: slow ease-in, slight overshoot, settle
    steps = 200
    s = np.linspace(0, 1, steps)
    # ease-in-out with slight overshoot
    demo = (45 * (6*s**5 - 15*s**4 + 10*s**3)
            + 8 * np.sin(np.pi * s) * (1 - s)**2)

    dmp = SingleJointDMP(n_bfs=50, alpha=25)
    dmp.learn_from_demo(demo)

    print("  Replaying learned motion to original goal (45°)...")
    t1, y1, dy1, f1 = dmp.rollout(start_deg=0, goal_deg=45, duration=2.0)

    print("  Replaying learned motion to NEW goal (70°) — shape adapts...")
    t2, y2, dy2, f2 = dmp.rollout(start_deg=0, goal_deg=70, duration=2.0)

    print("  Replaying from NEW start (20°) to original goal (45°)...")
    t3, y3, dy3, f3 = dmp.rollout(start_deg=20, goal_deg=45, duration=2.0)

    # plot all three overlaid
    fig, axes = plt.subplots(2, 1, figsize=(11, 6))
    fig.suptitle("DMP — Learn from demonstration, generalise to new goals",
                 fontsize=12, fontweight='bold')

    ax = axes[0]
    ax.plot(t1, y1, color='#534AB7', linewidth=2,
            label='original: 0°→45°')
    ax.plot(t2, y2, color='#1D9E75', linewidth=2, linestyle='--',
            label='new goal: 0°→70° (shape preserved)')
    ax.plot(t3, y3, color='#D85A30', linewidth=2, linestyle=':',
            label='new start: 20°→45°')
    ax.plot(np.linspace(0,2,steps),
            np.interp(np.linspace(0,2,steps),
                      np.linspace(0,2,steps), demo),
            color='#888780', linewidth=1, linestyle='--', alpha=0.5,
            label='original demo (grey)')
    ax.set_ylabel('angle (°)')
    ax.set_title('position — same learned shape, different start/goal')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    ax2 = axes[1]
    ax2.fill_between(t1, f1, alpha=0.2, color='#534AB7')
    ax2.plot(t1, f1, color='#534AB7', linewidth=1.5,
             label='forcing (original goal)')
    ax2.fill_between(t2, f2, alpha=0.2, color='#1D9E75')
    ax2.plot(t2, f2, color='#1D9E75', linewidth=1.5, linestyle='--',
             label='forcing (new goal)')
    ax2.set_ylabel('forcing f(s)')
    ax2.set_xlabel('time (s)')
    ax2.set_title('forcing function — same weights, scales with goal distance')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig("dmp_learn_from_demo.png", dpi=130, bbox_inches='tight')
    print("  Saved: dmp_learn_from_demo.png")
    plt.show()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

DEMOS = {
    'basic':     (demo_basic,           "Basic smooth motion — zero forcing, pure spring"),
    'goal_change':(demo_goal_change,    "Goal changes mid-motion — DMP adapts automatically"),
    'perturb':   (demo_perturb,         "Perturbation recovery — spring pulls back automatically"),
    'no_shake':  (demo_no_shake,        "Head shake no — oscillatory forcing function"),
    'surprised': (demo_surprised,       "Surprised recoil — negative forcing + underdamped"),
    'learn':     (demo_learn_from_demo, "Learn from demo — generalise to new goals"),
    'all':       (None,                 "Run all demos in sequence"),
}

def main():
    parser = argparse.ArgumentParser(
        description='DMP Single Joint Explorer',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--demo', default='basic',
        choices=list(DEMOS.keys()),
        help='\n'.join(f"  {k:15s} {v[1]}" for k,v in DEMOS.items()))
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  DMP Single Joint Explorer")
    print("="*55)
    print("\nAvailable demos:")
    for k, (_, desc) in DEMOS.items():
        marker = "→" if k == args.demo else " "
        print(f"  {marker} {k:15s} {desc}")
    print()

    if args.demo == 'all':
        for name, (fn, desc) in DEMOS.items():
            if fn is not None:
                print(f"\n{'─'*40}")
                print(f"Running: {desc}")
                fn()
    else:
        fn, desc = DEMOS[args.demo]
        print(f"Running: {desc}")
        fn()

    print("\nDone. PNG saved in current directory.")
    print("Next step: open dmp_explorer.py and modify the forcing")
    print("weights manually to create your own lamp motions.")


if __name__ == '__main__':
    main()