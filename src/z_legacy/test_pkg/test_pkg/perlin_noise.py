import noise
import numpy as np
import matplotlib.pyplot as plt


def perlin_noise(amp, time, freq, seed_offset):
    """
    Generate perlin noise
    """
    n = noise.pnoise1(time * freq, base=seed_offset)
    return amp*n


def main():
    time = np.arange(0.0, 10.0, 0.02)
    amp = 0.02
    freq = 0.3
    seed_offset = 100
    noise_values = []
    for t in time:
        noise_values.append(perlin_noise(amp, t, freq, seed_offset))
    plt.plot(time, noise_values)
    plt.show()


if __name__ == "__main__":
    main()
