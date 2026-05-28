"""Generate simple 8-bit style WAV sound effects for Space IO."""

import math
import random
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 44100
MAX_I16 = 32767
OUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "audio" / "sfx"


def square(phase):
    return 1.0 if math.sin(phase) >= 0 else -1.0


def triangle(phase):
    return 2.0 * abs(2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0) - 1.0


def write_wav(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for sample in samples:
            value = int(max(-1.0, min(1.0, sample)) * MAX_I16)
            frames.extend(struct.pack("<h", value))
        wav.writeframes(frames)


def tone(duration, start_freq, end_freq=None, volume=0.4, wave_fn=square, decay=0.0):
    end_freq = start_freq if end_freq is None else end_freq
    total = int(duration * SAMPLE_RATE)
    phase = 0.0
    samples = []
    for i in range(total):
        t = i / max(1, total - 1)
        freq = start_freq + (end_freq - start_freq) * t
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        env = 1.0 - decay * t
        samples.append(wave_fn(phase) * volume * max(0.0, env))
    return samples


def noise(duration, volume=0.4, decay=1.0):
    total = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(total):
        t = i / max(1, total - 1)
        env = (1.0 - t) ** decay
        samples.append(random.uniform(-1.0, 1.0) * volume * env)
    return samples


def mix(*tracks):
    length = max(len(track) for track in tracks)
    samples = []
    for i in range(length):
        value = 0.0
        for track in tracks:
            if i < len(track):
                value += track[i]
        samples.append(value / max(1.0, len(tracks) ** 0.5))
    return samples


def concat(*tracks):
    samples = []
    for track in tracks:
        samples.extend(track)
    return samples


def generate_sfx():
    random.seed(7)
    write_wav(OUT_DIR / "menu_select.wav", mix(
        tone(0.045, 120, 62, 0.42, square, 0.98),
        noise(0.024, 0.16, 3.4),
    ))
    write_wav(OUT_DIR / "menu_start.wav", concat(
        mix(
            tone(0.04, 105, 58, 0.44, square, 0.98),
            noise(0.024, 0.18, 3.6),
        ),
        tone(0.035, 0, 0, 0.0),
        mix(
            tone(0.055, 135, 68, 0.38, square, 0.98),
            noise(0.028, 0.14, 3.6),
        ),
    ))
    write_wav(OUT_DIR / "star_pickup.wav", concat(
        tone(0.06, 880, 1320, 0.26, square, 0.2),
        tone(0.08, 1320, 1760, 0.24, square, 0.35),
    ))
    write_wav(OUT_DIR / "boost.wav", mix(
        tone(0.35, 180, 520, 0.28, triangle, 0.15),
        tone(0.35, 360, 900, 0.18, square, 0.35),
    ))
    write_wav(OUT_DIR / "asteroid_bounce.wav", mix(
        tone(0.16, 180, 90, 0.4, square, 0.6),
        noise(0.16, 0.28, 1.8),
    ))
    write_wav(OUT_DIR / "mine_explosion.wav", mix(
        tone(0.42, 110, 45, 0.45, square, 0.9),
        noise(0.42, 0.55, 1.4),
    ))
    write_wav(OUT_DIR / "round_win.wav", concat(
        tone(0.10, 660, 660, 0.25, square, 0.2),
        tone(0.10, 880, 880, 0.25, square, 0.2),
        tone(0.18, 1320, 1320, 0.26, square, 0.4),
    ))
    write_wav(OUT_DIR / "return_to_menu.wav", mix(
        tone(0.07, 130, 54, 0.36, square, 0.98),
        noise(0.035, 0.14, 3.8),
    ))


def generate_engine():
    bucket_count = 48
    duration = 1.0
    total = int(duration * SAMPLE_RATE)
    for index in range(bucket_count):
        speed = index / (bucket_count - 1)
        idle_blend = 1.0 - speed
        firing_rate = 18.0 + 74.0 * speed
        sub_rate = firing_rate / 2.0
        exhaust_rate = firing_rate / 4.0
        wobble_rate = 2.0 + 5.0 * speed
        pulse_width = 0.10 - 0.045 * speed
        samples = []
        for i in range(total):
            t = i / SAMPLE_RATE
            phase = (firing_rate * t) % 1.0
            pulse_distance = min(phase, 1.0 - phase)
            pulse = math.exp(-((pulse_distance / pulse_width) ** 2))
            uneven_phase = (exhaust_rate * t + 0.08 * math.sin(2.0 * math.pi * wobble_rate * t)) % 1.0
            uneven = 0.75 + 0.25 * math.sin(2.0 * math.pi * uneven_phase)
            low_rumble = math.sin(2.0 * math.pi * sub_rate * t) * 0.38
            exhaust_thump = math.sin(2.0 * math.pi * exhaust_rate * t) * (0.32 + 0.22 * idle_blend)
            bark = math.sin(2.0 * math.pi * firing_rate * t) * pulse * (0.45 + 0.25 * speed)
            harmonic = math.sin(2.0 * math.pi * firing_rate * 2.0 * t) * pulse * 0.14
            grit = math.sin(2.0 * math.pi * (firing_rate * 3.0 + 7.0) * t) * pulse * 0.08
            sample = (low_rumble + exhaust_thump + bark + harmonic + grit) * uneven
            samples.append(sample * 0.62)
        write_wav(OUT_DIR / f"engine_{index:02d}.wav", samples)


def main():
    generate_sfx()
    generate_engine()


if __name__ == "__main__":
    main()
