"""
Generate synthetic EEG data for testing the EEG Rater application.
Creates 10 EDF files with varying patterns (normal and abnormal).
"""
import os
import numpy as np
from pathlib import Path

# Output directory
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = SCRIPT_DIR / "data" / "edf_files"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Standard 10-20 EEG channels (19 channels)
CHANNEL_NAMES = [
    'Fp1', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
    'T3', 'C3', 'Cz', 'C4', 'T4',
    'T5', 'P3', 'Pz', 'P4', 'T6',
    'O1', 'O2'
]

SFREQ = 256  # Sampling frequency in Hz
DURATION = 30  # Duration in seconds


def generate_filtered_noise(n_samples, sfreq, low_freq=0.5, high_freq=70):
    """Generate bandpass filtered noise that looks like EEG background."""
    # Generate white noise
    noise = np.random.randn(n_samples)

    # Apply simple smoothing to reduce sharp transients
    # This creates more natural-looking background activity
    kernel_size = max(1, int(sfreq / high_freq))
    kernel = np.ones(kernel_size) / kernel_size
    smoothed = np.convolve(noise, kernel, mode='same')

    return smoothed * 10  # Scale to reasonable EEG amplitude


def generate_oscillation(n_samples, sfreq, freq, amplitude, phase_noise=0.1):
    """Generate a neural oscillation with slight frequency variation."""
    t = np.arange(n_samples) / sfreq
    # Add slight frequency wobble for more natural look
    phase = 2 * np.pi * freq * t
    # Add slow phase noise
    phase_drift = np.cumsum(np.random.randn(n_samples) * phase_noise) / sfreq
    return amplitude * np.sin(phase + phase_drift)


def generate_base_eeg(n_channels, n_samples, sfreq):
    """Generate realistic-looking base EEG signal."""
    data = np.zeros((n_channels, n_samples))

    for ch in range(n_channels):
        # Background activity (filtered noise)
        background = generate_filtered_noise(n_samples, sfreq)

        # Alpha rhythm (8-13 Hz) - stronger in posterior channels
        alpha_amp = 25 if ch >= 12 else 12
        alpha_freq = 10 + np.random.uniform(-1, 1)
        alpha = generate_oscillation(n_samples, sfreq, alpha_freq, alpha_amp)

        # Beta rhythm (13-30 Hz) - smaller amplitude
        beta_amp = 5
        beta_freq = 18 + np.random.uniform(-2, 2)
        beta = generate_oscillation(n_samples, sfreq, beta_freq, beta_amp)

        # Theta rhythm (4-8 Hz)
        theta_amp = 6
        theta_freq = 6 + np.random.uniform(-1, 1)
        theta = generate_oscillation(n_samples, sfreq, theta_freq, theta_amp)

        # Combine - scale down to realistic total amplitude
        data[ch] = (background * 0.5 + alpha + beta + theta) * 0.8

        # Add very small high-frequency noise
        data[ch] += np.random.randn(n_samples) * 1

    return data


def add_spikes(data, sfreq, n_spikes=5, spike_amplitude=80):
    """Add epileptiform spikes - sharp but physiologically plausible."""
    n_channels, n_samples = data.shape

    for _ in range(n_spikes):
        spike_time = np.random.randint(int(0.1 * n_samples), int(0.9 * n_samples))
        affected_channels = np.random.choice(n_channels, size=np.random.randint(3, 8), replace=False)

        # Create spike waveform (~70ms duration, sharp rise, slower fall)
        spike_duration = int(0.07 * sfreq)  # ~18 samples
        t_spike = np.linspace(0, 1, spike_duration)

        # Spike shape: fast rise, slower fall with small afterwave
        spike_wave = np.zeros(spike_duration)
        rise_end = int(spike_duration * 0.25)
        fall_end = int(spike_duration * 0.7)

        spike_wave[:rise_end] = np.sin(np.linspace(0, np.pi/2, rise_end))
        spike_wave[rise_end:fall_end] = np.cos(np.linspace(0, np.pi/2, fall_end - rise_end))
        spike_wave[fall_end:] = -0.2 * np.sin(np.linspace(0, np.pi, spike_duration - fall_end))

        spike_wave *= spike_amplitude

        for ch in affected_channels:
            if spike_time + spike_duration < n_samples:
                amplitude_var = 0.7 + 0.6 * np.random.random()
                data[ch, spike_time:spike_time + spike_duration] += spike_wave * amplitude_var

    return data


def add_slowing(data, sfreq, intensity=1.0):
    """Add diffuse slowing (increased delta/theta)."""
    n_channels, n_samples = data.shape

    for ch in range(n_channels):
        # Delta activity (1-4 Hz)
        delta_freq = 2.5 + np.random.uniform(-0.5, 0.5)
        delta = generate_oscillation(n_samples, sfreq, delta_freq, 30 * intensity)

        # Extra theta
        theta_freq = 5 + np.random.uniform(-0.5, 0.5)
        theta = generate_oscillation(n_samples, sfreq, theta_freq, 20 * intensity)

        data[ch] += delta + theta

    return data


def add_burst_suppression(data, sfreq):
    """Add burst-suppression pattern."""
    n_channels, n_samples = data.shape

    # Create burst/suppression envelope
    envelope = np.zeros(n_samples)
    n_bursts = np.random.randint(4, 8)

    for _ in range(n_bursts):
        burst_center = np.random.randint(int(0.1 * n_samples), int(0.9 * n_samples))
        burst_width = int(np.random.uniform(0.3, 0.8) * sfreq)

        # Gaussian-shaped burst envelope
        t = np.arange(n_samples)
        burst = np.exp(-0.5 * ((t - burst_center) / (burst_width / 3)) ** 2)
        envelope = np.maximum(envelope, burst)

    # Apply envelope: suppress between bursts
    suppression_level = 0.05
    for ch in range(n_channels):
        data[ch] = data[ch] * (suppression_level + (1 - suppression_level) * envelope)

    return data


def add_rhythmic_discharge(data, sfreq, freq=3.0):
    """Add rhythmic epileptiform discharge."""
    n_channels, n_samples = data.shape

    rhythm = generate_oscillation(n_samples, sfreq, freq, 50)
    # Add harmonic
    rhythm += generate_oscillation(n_samples, sfreq, freq * 2, 20)

    for ch in range(n_channels):
        data[ch] += rhythm * (0.8 + 0.4 * np.random.random())

    return data


def add_asymmetry(data, sfreq):
    """Add hemispheric asymmetry."""
    n_channels = data.shape[0]
    left_channels = [0, 2, 3, 7, 8, 12, 13, 17]

    for ch in left_channels:
        if ch < n_channels:
            data[ch] *= 0.35

    return data


def write_edf(filename, data, channel_names, sfreq):
    """Write data to EDF format."""
    n_channels = len(channel_names)
    n_samples = data.shape[1]

    record_duration = 1
    samples_per_record = int(sfreq * record_duration)
    n_records = n_samples // samples_per_record
    data = data[:, :n_records * samples_per_record]

    physical_min = -200.0
    physical_max = 200.0
    digital_min = -32768
    digital_max = 32767

    scale = (physical_max - physical_min) / (digital_max - digital_min)
    data_clipped = np.clip(data, physical_min, physical_max)
    data_digital = ((data_clipped - physical_min) / scale + digital_min).astype(np.int16)

    with open(filename, 'wb') as f:
        f.write(b'0       ')
        f.write('X X X X'.ljust(80).encode('ascii'))
        f.write('Startdate 01-JAN-2024 X X X'.ljust(80).encode('ascii'))
        f.write(b'01.01.24')
        f.write(b'00.00.00')
        header_size = 256 + n_channels * 256
        f.write(str(header_size).ljust(8).encode('ascii'))
        f.write(b'EDF+C'.ljust(44))
        f.write(str(n_records).ljust(8).encode('ascii'))
        f.write(str(record_duration).ljust(8).encode('ascii'))
        f.write(str(n_channels).ljust(4).encode('ascii'))

        for name in channel_names:
            f.write(name.ljust(16).encode('ascii'))
        for _ in range(n_channels):
            f.write('AgAgCl electrode'.ljust(80).encode('ascii'))
        for _ in range(n_channels):
            f.write('uV'.ljust(8).encode('ascii'))
        for _ in range(n_channels):
            f.write(str(physical_min).ljust(8).encode('ascii'))
        for _ in range(n_channels):
            f.write(str(physical_max).ljust(8).encode('ascii'))
        for _ in range(n_channels):
            f.write(str(digital_min).ljust(8).encode('ascii'))
        for _ in range(n_channels):
            f.write(str(digital_max).ljust(8).encode('ascii'))
        for _ in range(n_channels):
            f.write('HP:0.5Hz LP:70Hz'.ljust(80).encode('ascii'))
        for _ in range(n_channels):
            f.write(str(samples_per_record).ljust(8).encode('ascii'))
        for _ in range(n_channels):
            f.write(' '.ljust(32).encode('ascii'))

        for rec in range(n_records):
            start = rec * samples_per_record
            end = start + samples_per_record
            for ch in range(n_channels):
                f.write(data_digital[ch, start:end].tobytes())

    print(f"Created: {filename}")


def main():
    np.random.seed(42)
    n_samples = DURATION * SFREQ
    n_channels = len(CHANNEL_NAMES)

    patterns = [
        ("sample_01_normal", "Normal EEG", None),
        ("sample_02_normal_variant", "Normal variant", None),
        ("sample_03_mild_slowing", "Mild slowing", lambda d: add_slowing(d, SFREQ, 0.4)),
        ("sample_04_moderate_slowing", "Moderate slowing", lambda d: add_slowing(d, SFREQ, 0.8)),
        ("sample_05_focal_spikes", "Focal spikes", lambda d: add_spikes(d, SFREQ, n_spikes=6, spike_amplitude=70)),
        ("sample_06_frequent_spikes", "Frequent spikes", lambda d: add_spikes(d, SFREQ, n_spikes=12, spike_amplitude=90)),
        ("sample_07_rhythmic_delta", "Rhythmic delta", lambda d: add_rhythmic_discharge(d, SFREQ, freq=2.5)),
        ("sample_08_asymmetry", "Asymmetry", lambda d: add_asymmetry(d, SFREQ)),
        ("sample_09_burst_suppression", "Burst suppression", lambda d: add_burst_suppression(d, SFREQ)),
        ("sample_10_mixed_abnormal", "Mixed abnormalities", lambda d: add_spikes(add_slowing(d, SFREQ, 0.5), SFREQ, n_spikes=4)),
    ]

    print(f"Generating {len(patterns)} synthetic EEG files...")
    print(f"Output directory: {OUTPUT_DIR}")
    print("-" * 60)

    for filename, description, modifier in patterns:
        data = generate_base_eeg(n_channels, n_samples, SFREQ)
        if modifier is not None:
            data = modifier(data)

        filepath = OUTPUT_DIR / f"{filename}.edf"
        write_edf(filepath, data, CHANNEL_NAMES, SFREQ)
        print(f"  Pattern: {description}")

    print("-" * 60)
    print(f"Done! {len(patterns)} files, {len(patterns) * (DURATION // 10)} snippets total")


if __name__ == "__main__":
    main()
