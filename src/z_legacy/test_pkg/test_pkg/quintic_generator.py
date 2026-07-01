import numpy as np
from matplotlib import pyplot as plt


def quintic_generator(q_start, q_end, v_start, v_end, a_start, a_end, T, dt):
    """generate quintic polynomial trajectory.
    q_start, q_end: start and end position in radians
    v_start, v_end: start and end velocity in radians/s
    a_start, a_end: start and end acceleration in radians/s^2
    T: total time
    dt: time step
    Returns:
        positions: list of position over time
        velocities: list of velocity over time
        accelerations: list of acceleration over time
        times: list of time over time
    """

    a0 = q_start
    a1 = v_start
    a2 = a_start / 2.0
    delta_q = q_end - q_start
    a3 = ( 20.0 * delta_q
        - (8.0 * v_end + 12.0 * v_start) * T
        - (3.0 * a_start - a_end) * T**2) / (2.0 * T**3)
    a4 = (-30.0 * delta_q
        + (14.0 * v_end + 16.0 * v_start) * T
        + (3.0 * a_start - 2.0 * a_end) * T**2 ) / (2.0 * T**4)
    a5 = (12.0 * delta_q
        - 6.0 * (v_end + v_start) * T
        + (a_end - a_start) * T**2 ) / (2.0 * T**5)

    times = np.linspace(0.0, T, int(T / dt)+1)
    positions = []
    velocities = []
    accelerations = []

    for t in times:
        pos = a0 + a1 * t + a2 * t**2 + a3 * t**3 + a4 * t**4 + a5 * t**5
        vel = a1 + 2 * a2 * t + 3 * a3 * t**2 + 4 * a4 * t**3 + 5 * a5 * t**4
        acc = 2 * a2 + 6 * a3 * t + 12 * a4 * t**2 + 20 * a5 * t**3
        positions.append(pos)
        velocities.append(vel)
        accelerations.append(acc)

    return positions, velocities, accelerations, times

def anticipation_trajectory(start, goal, T, dt, v_end, anticipation_scale=0.1, anticipation_temporal_scale=0.20, anticipation_vel=0.0, anticipation_acc=0.0):
    """generate quintic polynomial trajectory with anticipation.
    start, goal: start and end position in radians
    T: total time
    dt: time step
    anticipation_scale: scale of anticipation time
    Returns:
        positions: list of position over time
        velocities: list of velocity over time
        accelerations: list of acceleration over time
        times: list of time over time
    """
    direction = goal - start
    q_anticpation = start - anticipation_scale * direction  # 10% of travel distance.. move backward
    time_till_anticipation = T * anticipation_temporal_scale
    
    t1_pos, t1_vel, t1_acc, t1_times = quintic_generator(
                                                    q_start = start,
                                                    q_end = q_anticpation,
                                                    v_start = 0.0,
                                                    v_end = anticipation_vel,
                                                    a_start = 0.0,
                                                    a_end = anticipation_acc,
                                                    T = time_till_anticipation,
                                                    dt = dt
                                                    )

    t2_pos, t2_vel, t2_acc, t2_times = quintic_generator(
                                                    q_start = q_anticpation,
                                                    q_end = goal,
                                                    v_start = anticipation_vel,
                                                    v_end = v_end,
                                                    a_start = anticipation_acc,
                                                    a_end = 0.0,
                                                    T = T - time_till_anticipation,
                                                    dt = dt
                                                    )
    
    # add anticipation time to the t2_times
    t2_times = t2_times + time_till_anticipation    
    
    # merge the two trajectories end to end
    positions = np.concatenate((t1_pos[:-1], t2_pos))
    velocities = np.concatenate((t1_vel[:-1], t2_vel))
    accelerations = np.concatenate((t1_acc[:-1], t2_acc))
    times = np.concatenate((t1_times[:-1], t2_times))
    
    return positions, velocities, accelerations, times


def follow_through(start, 
                   goal, 
                   T, 
                   dt, 
                   v_end, 
                   anticipation_scale=0.1, 
                   anticipation_temporal_scale=0.20, 
                   anticipation_vel=0.0, 
                   anticipation_acc=0.0, 
                   omega=10, 
                   zeta=0.7,
                   ):
    positions, velocities, accelerations, times = anticipation_trajectory(
                                                        start = start,
                                                        goal = goal,
                                                        T = T,
                                                        dt = dt, 
                                                        v_end = v_end, 
                                                        anticipation_scale = anticipation_scale, 
                                                        anticipation_temporal_scale = anticipation_temporal_scale, 
                                                        anticipation_vel=anticipation_vel, 
                                                        anticipation_acc=anticipation_acc  
                                                    )

    follow_up_pos = []
    follow_up_vel = []
    follow_up_acc = []
    follow_up_times = []
    current_position = positions[-1]
    current_velocity = velocities[-1]
    current_time = times[-1]
    error = goal - current_position
    max_iterations = 5000
    iterations = 0

    while abs(error) > 0.01 or abs(current_velocity) > 0.01:
        iterations += 1
        if iterations > max_iterations:
            break
        
        acceleration = omega ** 2 * error - 2.0 * zeta * omega * current_velocity
        current_velocity += acceleration * dt
        current_position += current_velocity * dt
        current_time +=dt
        
        follow_up_pos.append(current_position)
        follow_up_vel.append(current_velocity)
        follow_up_acc.append(acceleration)
        follow_up_times.append(current_time)
        
        error = goal - current_position

    # merge the two trajectories end to end
    positions = np.concatenate((positions[:-1], follow_up_pos))
    velocities = np.concatenate((velocities[:-1], follow_up_vel))
    accelerations = np.concatenate((accelerations[:-1], follow_up_acc))
    times = np.concatenate((times[:-1], follow_up_times))

    return positions, velocities, accelerations, times



def main():
    q_start = 0.0
    q_end = 5.0
    T = 10.0
    dt = 0.02
    omega = 4.0
    zeta = 0.4
    v_end = 2.0
    positions, velocities, accelerations, times = follow_through(
                                                             start = q_start,
                                                             goal = q_end,
                                                             T = T,
                                                             dt = dt,
                                                             omega = omega,
                                                             zeta = zeta,
                                                             v_end = v_end,
                                                            )
    plt.plot(times, positions, label="Position")
    plt.plot(times, velocities, label="Velocity")
    plt.plot(times, accelerations, label="Acceleration")
    plt.xlabel("Time (s)")
    plt.ylabel("Value")
    plt.title("Quintic Polynomial Trajectory")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()
