#!/usr/bin/env python3
"""Learning checkpoint 1 — C++ vs. Python parser, side by side.

Runs the *same* test-log input through both the compiled C++ core (`sep_core`)
and the pure-Python fallback (`sep._pyfallback`), prints their output next to
each other to prove they agree, then benchmarks both on a large synthetic log
so you can see the speedup the C++ extension buys.

Run:
    python learn/01_cpp_vs_python_parser.py
    python learn/01_cpp_vs_python_parser.py --rows 500000

What to notice:
  * Identical results from two implementations behind one interface.
  * The FFI boundary: `sep_core` objects and Python dataclasses expose the
    same attribute names (die_id, test_name, value, pass_).
  * The benchmark is a lesson in itself: when the parser returns one Python
    object per row, *crossing the FFI boundary* (allocating hundreds of
    thousands of Python objects) dominates the runtime and masks the raw C++
    parse speed. The real-world win from C++ comes when you keep heavy work on
    the native side and hand back compact results — a key thing to internalize
    before reaching for an extension module.
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from sep import _pyfallback as py

try:
    import sep_core as cpp
except ImportError:  # pragma: no cover
    cpp = None

SAMPLE = """# die_id,test_name,value,lower_limit,upper_limit
D01,VDD_CORE,0.812,0.75,0.85
D01,IDDQ,95.0,0.0,90.0
D02,FMAX,2.71,2.20,3.20
D02,LEAKAGE,240.0,0.0,220.0
D03,VDD_CORE,0.690,0.75,0.85
"""


def show_side_by_side() -> None:
    print("=" * 68)
    print("Same input parsed by both backends")
    print("=" * 68)
    py_recs = py.parse_log_string(SAMPLE)
    cpp_recs = cpp.parse_log_string(SAMPLE) if cpp else None

    header = f"{'die':<5} {'test':<10} {'value':>8} | {'python':>7} | {'cpp':>7}"
    print(header)
    print("-" * len(header))
    for i, pr in enumerate(py_recs):
        cr = cpp_recs[i] if cpp_recs else None
        py_pass = "PASS" if pr.pass_ else "FAIL"
        cpp_pass = ("PASS" if cr.pass_ else "FAIL") if cr else "n/a"
        flag = "" if (cr is None or bool(cr.pass_) == bool(pr.pass_)) else "  <-- MISMATCH!"
        print(f"{pr.die_id:<5} {pr.test_name:<10} {pr.value:>8.3f} "
              f"| {py_pass:>7} | {cpp_pass:>7}{flag}")

    if cpp_recs is not None:
        agree = all(
            bool(a.pass_) == bool(b.pass_) and a.value == b.value
            for a, b in zip(py_recs, cpp_recs, strict=True)
        )
        print(f"\nBackends agree: {agree}")
    else:
        print("\n(sep_core not built — showing Python fallback only. "
              "Run `pip install -e .` to build the C++ core.)")


def benchmark(rows: int) -> None:
    print("\n" + "=" * 68)
    print(f"Benchmark: parsing {rows:,} rows")
    print("=" * 68)

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "big.log"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# die_id,test_name,value,lower_limit,upper_limit\n")
            for i in range(rows):
                fh.write(f"D{i:07d},FMAX,{2.0 + (i % 100) / 100:.3f},2.2,3.2\n")

        t0 = time.perf_counter()
        py_n = len(py.parse_log(str(path)))
        t_py = time.perf_counter() - t0
        print(f"python : {t_py*1000:8.1f} ms  ({py_n:,} records)")

        if cpp is not None:
            t0 = time.perf_counter()
            cpp_n = len(cpp.parse_log(str(path)))
            t_cpp = time.perf_counter() - t0
            print(f"cpp    : {t_cpp*1000:8.1f} ms  ({cpp_n:,} records)")
            if t_cpp > 0:
                print(f"\nC++ speedup: {t_py / t_cpp:.1f}x")
            print(
                "\nNote: both paths build one object per row, so the pybind11\n"
                "boundary crossing (allocating Python objects) dominates and the\n"
                "ratio stays near 1x. C++ pulls ahead when native code does the\n"
                "heavy lifting and returns compact results instead of N objects."
            )
        else:
            print("cpp    : n/a (extension not built)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=200_000,
                    help="rows for the benchmark log (default 200000)")
    args = ap.parse_args()

    print(f"C++ extension available: {cpp is not None}")
    show_side_by_side()
    benchmark(args.rows)


if __name__ == "__main__":
    main()
