#!/usr/bin/env python3
"""Learning checkpoint 2 — see the Schmoo edge move.

A "Schmoo plot" sweeps two parameters (here voltage x frequency) and marks each
point pass/fail. The pass region is bounded by an *edge*: a die can only reach a
maximum frequency that scales with voltage. This script draws that Schmoo as a
colored ASCII grid and lets you change the parameters so you can watch the edge
shift — building intuition for what the dashboard's Schmoo heatmap shows.

Run:
    python learn/02_schmoo_edge.py
    python learn/02_schmoo_edge.py --fmax-scale 1.2      # healthier die
    python learn/02_schmoo_edge.py --fmax-scale 0.8      # weaker die
    python learn/02_schmoo_edge.py --noise 0.15          # more measurement noise

What to notice:
  * Raising --fmax-scale pushes the pass region up (die runs faster).
  * The edge is a curve, not a line, because max frequency scales with voltage.
  * Noise fuzzes the boundary — exactly what real bench data looks like.

This mirrors the model in sep/datagen/generator.py.
"""

from __future__ import annotations

import argparse

import numpy as np

GREEN = "\033[42m \033[0m"   # pass cell
RED = "\033[41m \033[0m"     # fail cell


def fmax_at_voltage(v: float, scale: float) -> float:
    """Max reachable frequency at voltage v (matches the data generator)."""
    return (0.8 + 2.6 * (v - 0.6)) * scale


def build_grid(vlo, vhi, flo, fhi, steps, scale, noise, seed):
    rng = np.random.default_rng(seed)
    voltages = np.linspace(vlo, vhi, steps)
    freqs = np.linspace(flo, fhi, steps)
    grid = np.zeros((steps, steps), dtype=int)
    for xi, v in enumerate(voltages):
        edge = fmax_at_voltage(v, scale)
        for yi, f in enumerate(freqs):
            margin = edge - f + rng.normal(0, noise)
            grid[yi, xi] = 1 if margin > 0 else 0
    return voltages, freqs, grid


def draw(voltages, freqs, grid) -> None:
    steps = len(freqs)
    # High frequency at the top.
    for yi in range(steps - 1, -1, -1):
        label = f"{freqs[yi]:4.2f}"
        cells = "".join(GREEN if grid[yi, xi] else RED for xi in range(steps))
        print(f"{label} |{cells}")
    print("     +" + "-" * steps)
    # Voltage axis labels (sparse; gap >= 6 so 4-char labels don't collide).
    ticks = [" "] * (steps + 4)
    gap = max(6, steps // 4)
    for xi in range(0, steps, gap):
        s = f"{voltages[xi]:.2f}"
        for k, ch in enumerate(s):
            ticks[xi + k] = ch
    print("      " + "".join(ticks) + "  (voltage, V)")
    passed = int(grid.sum())
    total = grid.size
    print(f"\nfrequency (GHz) on Y   |   pass cells: {passed}/{total} "
          f"({100*passed/total:.1f}%)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vlo", type=float, default=0.65)
    ap.add_argument("--vhi", type=float, default=0.95)
    ap.add_argument("--flo", type=float, default=1.0)
    ap.add_argument("--fhi", type=float, default=3.4)
    ap.add_argument("--steps", type=int, default=24)
    ap.add_argument("--fmax-scale", type=float, default=1.0,
                    help="die health; >1 faster, <1 slower")
    ap.add_argument("--noise", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    print(f"Schmoo: voltage[{args.vlo},{args.vhi}] x frequency[{args.flo},{args.fhi}] "
          f"| fmax_scale={args.fmax_scale} noise={args.noise}\n")
    v, f, g = build_grid(args.vlo, args.vhi, args.flo, args.fhi, args.steps,
                         args.fmax_scale, args.noise, args.seed)
    draw(v, f, g)


if __name__ == "__main__":
    main()
