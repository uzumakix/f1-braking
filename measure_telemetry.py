"""
Measure what the telemetry actually is, before claiming anything about it.

Answers three questions with numbers:
  1. how often does a speed sample arrive
  2. where and how hard does each driver brake into Turn 1
  3. how closely does the computed braking onset match the car's own brake channel

Run:  python measure_telemetry.py
"""

from __future__ import annotations

import numpy as np

import fastf1

fastf1.Cache.enable_cache("cache")

SESSION_YEAR = 2023
DRIVERS = ["VER", "SAI"]
ZONE = (600.0, 1050.0)  # metres from the start line, the Turn 1 braking zone

print("loading 2023 Italian Grand Prix qualifying ...")
session = fastf1.get_session(SESSION_YEAR, "Italian Grand Prix", "Q")
session.load(telemetry=True, weather=False, messages=False)

results = {}

for drv in DRIVERS:
    lap = session.laps.pick_drivers(drv).pick_fastest()
    tel = lap.get_car_data().add_distance()

    t = tel["Time"].dt.total_seconds().to_numpy()
    v_kmh = tel["Speed"].to_numpy(dtype=float)
    dist = tel["Distance"].to_numpy(dtype=float)
    brake = tel["Brake"].to_numpy()

    dt = np.diff(t)
    print(f"\n=== {drv} ===")
    print(f"  samples on the lap        : {len(t)}")
    print(f"  median gap between samples: {np.median(dt)*1000:.1f} ms")
    print(f"  mean gap                  : {np.mean(dt)*1000:.1f} ms")
    print(f"  5th to 95th percentile gap: {np.percentile(dt,5)*1000:.1f} to {np.percentile(dt,95)*1000:.1f} ms")
    print(f"  implied rate              : {1.0/np.median(dt):.2f} Hz")

    v = v_kmh / 3.6
    accel = np.gradient(v, t)
    g = accel / 9.81

    in_zone = (dist >= ZONE[0]) & (dist <= ZONE[1])
    if not in_zone.any():
        print("  no samples in the braking window")
        continue

    gz = g[in_zone]
    dz = dist[in_zone]
    tz = t[in_zone]
    bz = brake[in_zone]

    peak_i = int(np.argmin(gz))
    print(f"  peak deceleration         : {gz[peak_i]:.2f} G at {dz[peak_i]:.0f} m")
    print(f"  top speed before the zone : {v_kmh[in_zone].max():.1f} km/h")

    # brake onset from the car's own brake channel
    bz_bool = bz.astype(bool)
    onset_channel = int(np.argmax(bz_bool)) if bz_bool.any() else None

    # brake onset from the computed derivative: first sample under -1 G
    under = np.where(gz < -1.0)[0]
    onset_computed = int(under[0]) if len(under) else None

    if onset_channel is not None and onset_computed is not None:
        gap_s = tz[onset_computed] - tz[onset_channel]
        gap_m = dz[onset_computed] - dz[onset_channel]
        frames = onset_computed - onset_channel
        print(f"  brake point (car channel) : {dz[onset_channel]:.0f} m")
        print(f"  brake point (computed)    : {dz[onset_computed]:.0f} m")
        print(f"  difference                : {frames} samples, {gap_s*1000:.0f} ms, {gap_m:.0f} m")
        results[drv] = dict(
            brake_m=float(dz[onset_channel]),
            peak_g=float(gz[peak_i]),
            peak_at_m=float(dz[peak_i]),
            median_gap_ms=float(np.median(dt) * 1000),
            gap_frames=int(frames),
            gap_ms=float(gap_s * 1000),
            gap_m=float(gap_m),
            vmax=float(v_kmh[in_zone].max()),
        )

if len(results) == 2:
    a, b = DRIVERS
    print(f"\n=== comparison ===")
    print(f"  {b} brakes {results[b]['brake_m']-results[a]['brake_m']:.0f} m "
          f"{'later' if results[b]['brake_m']>results[a]['brake_m'] else 'earlier'} than {a}")
    print(f"  peak G: {a} {results[a]['peak_g']:.2f}, {b} {results[b]['peak_g']:.2f}")

print("\ndone.")
