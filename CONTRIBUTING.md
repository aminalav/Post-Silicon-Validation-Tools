# Developing & Learning Guide

This doc has two jobs:

1. **Dev setup** — get a working environment and know the common commands.
2. **A code-reading tour** — the fastest path to *understanding* the codebase,
   ordered so each step builds on the last. Great if you're using this project
   to learn C++/pybind11, SQL, or full-stack Python.

---

## 1. Environment setup

Prerequisites:

- **Python 3.10+**
- **A C++17 compiler** (clang or gcc) — for the compiled core
- **CMake** — pulled automatically by the build if missing, but installing it
  system-wide (`brew install cmake ninja`) makes rebuilds faster
- **Node 20+** — for the dashboard

```bash
# Python env + compile the C++ extension in one step
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Confirm the compiled core is active (should print: cpp)
sep info

# Seed data + DB + a report, then serve
sep demo
sep serve                 # http://localhost:8000/docs

# Dashboard (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

> **PDF reports** are optional and need a heavier dependency:
> `pip install -e ".[dev,reports]"`, then `sep report LOT001 --pdf`.

---

## 2. Common tasks

| Task | Command |
|---|---|
| Regenerate synthetic data | `sep generate --out data --wafers 3` |
| Load a lot into the DB | `sep ingest data/LOT001` |
| Print yield summary | `sep yields` |
| Decode a register value | `sep decode 0xA000830D` |
| Run the API | `sep serve` |
| One-shot pipeline | `sep demo` |
| Run tests | `pytest -q` |
| Lint | `ruff check sep tests` |
| Format | `black sep tests` |
| Type-check | `mypy sep` |

### Rebuilding the C++ extension

On-demand editable rebuild is intentionally **off** (it would require `cmake`
on `PATH` at import time). So after editing anything in `cpp/`, recompile with:

```bash
pip install -e .
```

If the compiled module ever fails to load, the platform automatically falls
back to a pure-Python implementation (`sep/core.py`) — `sep info` will then
print `python` instead of `cpp`. That's the safety net; for the C++ learning
goal you want it saying `cpp`.

---

## 3. Code-reading tour (recommended order)

Follow the data as it flows through the system. Each file is small and focused.

### Step 1 — What the data *is*: `sep/datagen/generator.py`
Start here. It models realistic post-silicon behavior: parametric tests with
process-corner variation, Schmoo sweeps (a die's max frequency scales with
voltage → a believable failing edge), radial wafer yield loss, and register
dumps. Understanding the data shape makes everything downstream obvious.
Outputs: `tests.log`, `dies.csv`, `schmoo.csv`, `registers.csv`.

### Step 2 — The C++ core: `cpp/`
This is the C/C++ learning centerpiece.
- `include/sep/log_parser.hpp` + `src/log_parser.cpp` — a streaming, zero-copy
  (`std::string_view`) parser. Read this to learn buffered I/O, tokenizing
  without allocations, and `std::from_chars`.
- `include/sep/reg_decoder.hpp` + `src/reg_decoder.cpp` — bitfield extraction
  with masks/shifts (note the guard against the undefined-behavior 64-bit
  shift), plus an expected-vs-actual compare.
- `bindings/bindings.cpp` — **the FFI boundary**. See how pybind11 turns C++
  `struct`s into Python classes and `std::vector<T>` into Python lists. This is
  the single most transferable concept in the repo.
- `CMakeLists.txt` (repo root) — how the module is compiled and named
  `sep_core`.

### Step 3 — The Python/C++ seam: `sep/core.py`
Shows the `try: import sep_core / except ImportError:` pattern that prefers the
compiled module but degrades gracefully to pure Python behind an identical
interface. Compare the two implementations side by side — same behavior, two
languages.

### Step 4 — Storage: `sep/db/models.py` then `sep/db/ingest.py`
- `models.py` — SQLAlchemy 2.0 typed models mirroring real test hierarchy
  (`lot → wafer → die → test → measurement`, plus `schmoo`, `reg_dump`).
- `ingest.py` — loads the generated files into the DB. Note it parses
  `tests.log` via `sep.core` (so the C++ core is on the real data path).

### Step 5 — Analysis: `sep/analysis/analysis.py`
pandas aggregations that produce the numbers the UI/report consume: yield
summary, failure Pareto, Schmoo matrix, wafer map. Queries are parameterized
(`text(...)` with bound params) — a good SQL-safety habit to notice.

### Step 6 — Serving it: `sep/api/app.py` and `frontend/src/App.jsx`
- `app.py` — thin FastAPI layer over the analysis functions.
- `App.jsx` — React fetches those endpoints and renders Plotly charts. The
  wafer map and Schmoo heatmap are the domain "wow" visuals.

### Step 7 — Reporting: `sep/reports/`
Jinja2 renders `template.html.j2` from the same analysis outputs, optionally to
PDF. Cheap to build once the DB exists; high perceived value.

---

## 4. Learning checkpoints

Runnable, dependency-free scripts in [`learn/`](learn/) that build intuition:

```bash
python learn/01_cpp_vs_python_parser.py   # C++ vs Python parser + benchmark
python learn/02_schmoo_edge.py            # move the Schmoo pass/fail edge
```

See [`learn/README.md`](learn/README.md) for what each one teaches.

## 5. How to extend it (good first exercises)

- **Add a test** to `tests/` — e.g., assert Schmoo pass-rate rises with voltage.
- **Add an API endpoint** — surface `sep/analysis` output not yet exposed
  (e.g., per-corner yield), then chart it in `App.jsx`.
- **Enrich the C++ parser** — support a second log line format or a real-ish
  header, then update `test_core.py`. Recompile with `pip install -e .`.
- **Add a register spec** in `specs/` and wire `/api/registers` to select it.

Before pushing, keep CI green:

```bash
ruff check sep tests && pytest -q
```

---

## 6. Project layout

```
cpp/        C++ core (log parser, register decoder) + pybind11 bindings
sep/        Python package: datagen, db, analysis, api, reports, cli, core
frontend/   React + Vite dashboard (Plotly)
specs/      Example register specification
tests/      pytest suite (core + end-to-end pipeline)
docs/       Screenshots and assets
```

See [`BUILD_PLAN.md`](BUILD_PLAN.md) for the design rationale and roadmap.
