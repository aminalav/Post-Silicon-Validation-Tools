# Learning checkpoints

Small, self-contained scripts to build intuition for the two most instructive
parts of this project. They have no dependencies beyond the package itself
(install with `pip install -e ".[dev]"` from the repo root first).

## 1. C++ vs. Python parser — `01_cpp_vs_python_parser.py`

Runs the same test log through the compiled C++ core and the pure-Python
fallback, prints them side by side to prove they agree, then benchmarks both.

```bash
python learn/01_cpp_vs_python_parser.py
python learn/01_cpp_vs_python_parser.py --rows 500000   # bigger benchmark
```

Teaches: the pybind11 FFI boundary, the fallback pattern, and why a
streaming/zero-copy C++ parser matters for large validation logs.

## 2. The Schmoo edge — `02_schmoo_edge.py`

Draws a voltage × frequency Schmoo as a colored ASCII grid and lets you move the
pass/fail edge by changing parameters.

```bash
python learn/02_schmoo_edge.py                    # baseline
python learn/02_schmoo_edge.py --fmax-scale 1.2   # healthier (faster) die
python learn/02_schmoo_edge.py --fmax-scale 0.8   # weaker die
python learn/02_schmoo_edge.py --noise 0.15       # noisier boundary
```

Teaches: what a Schmoo plot represents and how the synthetic data in
`sep/datagen/generator.py` models a realistic failing edge.
