# Braking analysis from Formula 1 telemetry, Monza 2023

Takes the speed trace of a qualifying lap, differentiates it, and reads off where a driver starts
braking for Turn 1 and how hard. The comparison is Verstappen against Sainz in the 2023 Italian Grand
Prix qualifying session, and the output is a braking profile laid out against distance along the
track rather than against time, so two laps run at different speeds still line up at the same point
on the circuit.

![Speed and deceleration through the Turn 1 braking zone for both drivers](results/braking_analysis.png)

![Full-lap speed trace with the Turn 1 braking zone marked](results/full_lap_speed.png)

## How it works

**Getting the data.** `pipeline.py` pulls speed, throttle, brake and distance channels for the fastest
qualifying lap of each driver through the FastF1 library, which wraps the published timing feed.

**The maths.** Speed arrives in km/h and is converted to m/s. Longitudinal acceleration is the
derivative of speed with respect to time, computed with `numpy.gradient`, which uses a central
difference and is therefore second-order accurate on evenly spaced samples. Dividing by 9.81 puts the
result in G, which is how the figure is labelled because that is the unit the sport uses.

No smoothing is applied before differentiating. Smoothing first would shift the braking point, since
any filter with a window wider than a sample drags a sharp edge later in time, and the braking point
is exactly the sharp edge being measured. The dashboard applies a five-sample average for display
only, after the derivative has been taken.

**Picking the zone.** The braking zone is cut out by distance, from 600 to 1050 metres past the start
line, rather than by time. Two drivers reach Turn 1 at different moments, so a time window would
compare different parts of the corner; a distance window compares the same stretch of tarmac.

## Checking the data before trusting it

`measure_telemetry.py` exists to answer the questions that have to come before any result: how often a
speed sample actually arrives, what the gap between samples is at the fifth and ninety-fifth
percentile, and how far apart the braking onset computed from the derivative sits from the car's own
brake channel, measured in samples, milliseconds and metres.

Run it before quoting any number from this repository:

```bash
pip install -r requirements.txt
python measure_telemetry.py
```

It prints the sampling interval it measured rather than relying on any assumed figure, which matters:
the published feed is far coarser than a car's internal sensors, and the resolution of the braking
point can be no finer than the gap between two samples. The figures above were produced by an earlier
run of the pipeline; `measure_telemetry.py` regenerates the underlying numbers from scratch.

## Running the rest

Static figures:

```bash
python generate_plots.py
```

Interactive dashboard:

```bash
streamlit run dashboard.py
```

First run downloads the session from the timing servers and caches it locally.

## Limits

- Deceleration here is kinematic, worked out from how the speed changes. It is not a measurement of
  force at the tyre, and it folds in aerodynamic drag, engine braking and the brakes themselves
  without separating them.
- Two laps, two drivers, one corner. Nothing here says anything general about either car.
- The resolution of the braking point is bounded by the sampling interval of the published feed, which
  is why the script above measures that interval rather than assuming it.
- Speed is scalar. Lateral acceleration through the corner is not part of this.

## References

1. Milliken, W. F. & Milliken, D. L. (1995). *Race Car Vehicle Dynamics*. SAE International.
2. FastF1: [theOehrly/Fast-F1](https://github.com/theOehrly/Fast-F1).

## License

[MIT](LICENSE)
