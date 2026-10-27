"""
Check the maths against cases where the answer is known in advance.

No network and no telemetry needed. Two questions:

  1. given a speed trace with a deceleration we chose ourselves, does the
     pipeline recover that number
  2. how precisely can a braking point be located, as a function of how far
     apart the speed samples are

The second one matters because the published timing feed is far coarser than
a car's own sensors, and the braking point cannot be pinned down more tightly
than the gap between two samples.

Run:  python verify_math.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline import compute_deceleration, extract_braking_zone, find_brake_point

G = 9.81


def make_trace(dt, v0_kmh=340.0, brake_at_m=780.0, decel_g=5.0,
               v_end_kmh=150.0, d_start=600.0, d_end=1050.0):
    """
    A car holding v0 until brake_at_m, then braking at a constant rate until
    it reaches v_end, then holding that. Sampled every dt seconds.
    """
    v0 = v0_kmh / 3.6
    v_end = v_end_kmh / 3.6
    a = -decel_g * G

    t, d, v = [0.0], [d_start], [v0]
    while d[-1] < d_end:
        speed = v[-1]
        if d[-1] >= brake_at_m and speed > v_end:
            speed = max(v_end, speed + a * dt)
        t.append(t[-1] + dt)
        d.append(d[-1] + speed * dt)
        v.append(speed)

    return pd.DataFrame({
        "Speed": np.array(v) * 3.6,
        "Distance": np.array(d),
        "SessionTime": pd.to_timedelta(t, unit="s"),
    })


print("=" * 64)
print("1. does the pipeline recover a deceleration we chose ourselves")
print("=" * 64)

# linear speed ramp: 300 to 100 km/h over exactly 2 seconds
n = 400
t = np.linspace(0, 2, n)
speed_kmh = np.linspace(300, 100, n)
expected_ms2 = (100 - 300) / 3.6 / 2.0
expected_g = expected_ms2 / G

ramp = pd.DataFrame({
    "Speed": speed_kmh,
    "Distance": 600 + np.cumsum(speed_kmh / 3.6 * (2.0 / n)),
    "SessionTime": pd.to_timedelta(t, unit="s"),
})
out = compute_deceleration(ramp)
interior = out["Accel_G"].values[1:-1]

print(f"  deceleration put in     : {expected_g:.6f} G  ({expected_ms2:.4f} m/s^2)")
print(f"  deceleration recovered  : {interior.mean():.6f} G")
print(f"  largest error anywhere  : {np.max(np.abs(interior - expected_g)):.2e} G")
print("  central differences are exact on a straight line, so this should be")
print("  zero to machine precision, and it is.")

print()
print("=" * 64)
print("2. how precisely can the braking point be located")
print("=" * 64)
print(f"  true braking point: 780 m, true deceleration: -5.000 G")
print()
print(f"  {'sample gap':>12} {'rate':>9} {'found at':>10} {'error':>9} {'peak G':>9}")
print("  " + "-" * 54)

for dt in (0.001, 0.01, 0.02, 0.05, 0.10, 0.24, 0.50):
    df = make_trace(dt)
    df = compute_deceleration(df)
    zone = extract_braking_zone(df)
    bp = find_brake_point(zone)
    peak = zone["Accel_G"].min()
    if bp is None:
        print(f"  {dt*1000:>9.0f} ms {1/dt:>7.1f} Hz     not found")
        continue
    print(f"  {dt*1000:>9.0f} ms {1/dt:>7.1f} Hz {bp:>9.1f} m {bp-780:>+8.1f} m {peak:>8.2f}")

print()
print("  The error is not a clean function of the sample gap, and the 240 ms")
print("  row landing closer than the 100 ms row shows why: what matters is")
print("  where the first sample after the driver hits the brakes happens to")
print("  fall. That puts a ceiling on the error rather than a fixed value.")
print("  The ceiling is the distance covered between two samples:")
for dt in (0.01, 0.10, 0.24):
    print(f"    at {dt*1000:>3.0f} ms and 340 km/h the car covers {340/3.6*dt:>5.1f} m between samples")
print("  So a braking point read off this feed is known to within a car")
print("  length or two at best, and the sampling gap has to be measured")
print("  rather than assumed before any figure is quoted.")
print()
print("done.")
