# Silicon Engineering Platform — Build Plan

> A post-silicon validation analytics platform. Ingests test logs, register
> dumps, and Schmoo sweeps; stores them in a relational DB; runs yield/failure
> analysis; and surfaces everything through a dashboard with Schmoo plots and
> wafer maps, plus automated reports.

---

## 1. Goals

This project serves three explicit goals:

1. **Learn / build toward domain expertise** in post-silicon validation data flows.
2. **Position for pre- and post-silicon validation roles** (this project targets the *post-silicon* side; a separate RTL design & verification portfolio covers pre-silicon).
3. **Grow C/C++ and Python.** C++ is deliberately on the critical path (parsing + register decode via a Python extension), not decorative.

**Time budget:** 2 focused weeks.

**Skill calibration:** Comfortable with C/C++, stronger in Python. Plan pushes C++ into performance/FFI territory (CMake + pybind11) and Python toward production patterns (typed, tested, packaged).

---

## 2. What "post-silicon validation" means here (domain primer)

Post-silicon validation happens *after* first silicon comes back from the fab. Engineers run the real chip on bench/ATE (automated test equipment) to characterize behavior, find bugs, and assess yield. Key artifacts this platform models:

- **Test logs** — per-unit records of tests run, measured values, pass/fail vs. limits.
- **Register dumps** — raw hex values of hardware registers; decoded into named bitfields to debug state.
- **Schmoo plots** — 2D pass/fail maps sweeping two parameters (classically **voltage × frequency**). The "shmoo" shows the operating envelope and where the part fails.
- **Wafer maps** — spatial pass/fail (or bin) map of dies across a wafer; reveals systematic spatial defects.
- **Yield & failure analysis** — what fraction passed, which tests fail most (Pareto), binning.

Because real ATE data (e.g., STDF) is proprietary/NDA-locked, we **generate realistic synthetic data** — itself a portfolio talking point (you modeled realistic silicon failure behavior).

---

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Data generation | Python (numpy) | Fast to model realistic failure distributions |
| Core parser | **C++17** + **pybind11**, built with **CMake** | Performance + the C/C++ learning core (FFI boundary) |
| Register decoder | **C++17** | Bitfield/mask/shift work; canonical hardware-adjacent C++ |
| Orchestration / analysis | Python 3.11+ (pandas) | Strength area; glue + analytics |
| Database | **SQLite** (schema Postgres-portable via SQLAlchemy) | Zero-setup demo; production-shaped |
| API | **FastAPI** (+ Pydantic) | Typed, modern, auto docs |
| Frontend | **React** + **Vite** + a charting lib (Plotly/ECharts) | Schmoo + wafer map visuals |
| Reports | HTML → PDF (Jinja2 + WeasyPrint or Playwright) | Cheap, high perceived value |
| Packaging | **Docker Compose** | `up` and it runs with seeded data |
| Tooling | Git, pytest, ruff/black, mypy, GitHub Actions (stretch) | Production hygiene |

---

## 4. Architecture

```
                +------------------------+
                |  Synthetic Data Gen    |  (Python)
                |  logs / regs / schmoo  |
                +-----------+------------+
                            | files (text/CSV/JSON)
                            v
        +-------------------------------------------+
        |  C++ core (built as pybind11 module)      |
        |  - streaming log parser                   |
        |  - register decoder / compare             |
        +----------------------+--------------------+
                               | structured records (Python objects)
                               v
        +-------------------------------------------+
        |  Ingest layer (Python + SQLAlchemy)       |
        +----------------------+--------------------+
                               v
                     +---------------------+
                     |   SQLite database   |
                     +----------+----------+
                                |
             +------------------+------------------+
             v                                     v
   +--------------------+                +----------------------+
   |  Analysis (pandas) |                |  FastAPI backend     |
   |  yield / Pareto /  |--------------->|  REST endpoints      |
   |  schmoo / wafermap |                +----------+-----------+
   +--------------------+                           |
             |                                      v
             v                          +-----------------------+
   +--------------------+               |  React dashboard      |
   |  Report generator  |               |  schmoo + wafer map   |
   |  (HTML -> PDF)      |               +-----------------------+
   +--------------------+
```

---

## 5. Repository structure

```
silicon-engineering-platform/
├── README.md
├── BUILD_PLAN.md
├── docker-compose.yml
├── pyproject.toml                # Python packaging + tool config
├── CMakeLists.txt                # top-level CMake for the C++ module
├── cpp/                          # C++ core
│   ├── CMakeLists.txt
│   ├── include/sep/
│   │   ├── log_parser.hpp
│   │   └── reg_decoder.hpp
│   ├── src/
│   │   ├── log_parser.cpp
│   │   └── reg_decoder.cpp
│   └── bindings/
│       └── bindings.cpp          # pybind11 glue -> module `sep_core`
├── sep/                          # Python package
│   ├── __init__.py
│   ├── datagen/                  # synthetic data generator
│   ├── db/                       # SQLAlchemy models + ingest
│   ├── analysis/                 # yield, pareto, schmoo, wafermap
│   ├── api/                      # FastAPI app
│   └── reports/                  # report generation
├── frontend/                     # React + Vite app
├── tests/                        # pytest (Python) + ctest (C++)
├── data/                         # generated sample data (gitignored large)
└── specs/                        # register spec files (JSON/YAML)
```

---

## 6. Data model (SQL schema)

Designed hierarchically to mirror real silicon test data and to stay Postgres-portable.

```
lot        (lot_id PK, product, process_corner, created_at)
wafer      (wafer_id PK, lot_id FK, wafer_number)
die        (die_id PK, wafer_id FK, x, y, final_bin)
test       (test_id PK, name, unit, lower_limit, upper_limit)
measurement(meas_id PK, die_id FK, test_id FK, value, pass)
schmoo     (schmoo_id PK, die_id FK, param_x, param_y, x_val, y_val, pass)
reg_dump   (dump_id PK, die_id FK, reg_name, raw_value, timestamp)
```

- `die.final_bin` supports yield binning and wafer maps.
- `schmoo` rows are one point per (x_val, y_val) sweep coordinate.
- Keep the schema in SQLAlchemy models so SQLite→Postgres is a URL change.

---

## 7. The C++ learning core (details)

This is where C/C++ growth happens. Two deliverables:

### 7a. Streaming log parser (`cpp/src/log_parser.cpp`)
- **Goal:** parse large test-log files into structured records efficiently.
- **Learn:** buffered file I/O, `std::string_view` zero-copy tokenizing, `struct`/`enum class`, `std::vector`, error handling, and the pybind11 boundary (return a `std::vector<Record>` that becomes a Python list of objects).
- **Interface sketch:**

```cpp
struct TestRecord {
    std::string die_id;
    std::string test_name;
    double value;
    bool pass;
};
std::vector<TestRecord> parse_log(const std::string& path);
```

### 7b. Register decoder / compare (`cpp/src/reg_decoder.cpp`)
- **Goal:** decode a raw register value into named bitfields from a spec; compare expected vs. actual.
- **Learn:** bit masks/shifts, packed field extraction, `enum` decoding, spec-driven design.
- **Interface sketch:**

```cpp
struct Field { std::string name; uint32_t lsb, width; };
struct DecodedField { std::string name; uint64_t value; };
std::vector<DecodedField> decode(uint64_t raw, const std::vector<Field>& spec);
```

### 7c. pybind11 + CMake
- `bindings/bindings.cpp` exposes both as module `sep_core`.
- Build via CMake; verify `import sep_core` works from Python and round-trips data.
- **Milestone gate:** Python test that parses a generated log through the C++ module and asserts record counts/values.

> If build/tooling eats time, the fallback is a pure-Python parser behind the *same* interface so downstream work is never blocked — but the C++ path is the learning goal, so protect it.

---

## 8. Two-week schedule

### Week 1 — data, C++ core, storage

**Day 1–2 · Synthetic data generator** *(Python)*
- Generate test logs, register dumps, and Schmoo sweeps.
- Realistic behavior: pass/fail vs. limits, a believable Schmoo failing edge (e.g., fails at low V / high F), process-corner variation, systematic + random wafer defects.
- **DoD:** `python -m sep.datagen --out data/` produces a full sample lot.

**Day 3–5 · C++ core + pybind11 + CMake**
- Implement log parser (7a); wire bindings; get `import sep_core` working.
- **DoD:** pytest parses a generated log via `sep_core` and validates output. Biggest learning block — buffer time here.

**Day 6–7 · SQL schema + ingest**
- SQLAlchemy models (§6); ingest parser output into SQLite.
- **DoD:** `python -m sep.db.ingest data/` populates the DB; a query returns yield per wafer.

### Week 2 — analysis, visualization, web, polish

**Day 8–9 · C++ register decoder + compare**
- Implement decoder (7b); add to bindings; spec files in `specs/`.
- **DoD:** decode a dump into named fields; compare expected vs. actual and flag mismatches.

**Day 10 · Yield & failure analysis** *(Python/pandas)*
- Yield summary, failing-test Pareto, bin summary, wafer-map matrix, Schmoo matrix.
- **DoD:** functions return tidy structures the API can serve directly.

**Day 11–12 · FastAPI + React dashboard**
- Endpoints: lots/wafers, yield summary, Schmoo data, wafer-map data, decoded registers.
- React views: **Schmoo plot** + **wafer map** (the two "wow" visuals) + a summary table.
- **DoD:** dashboard renders live data from the DB.

**Day 13 · Automated report generation**
- Jinja2 HTML → PDF summary (yield, top failures, sample Schmoo/wafer image).
- **DoD:** `python -m sep.reports --lot <id>` writes a PDF.

**Day 14 · Polish & ship**
- `docker compose up` brings up API + frontend with seeded data (<60s to demo).
- README: architecture diagram, screenshots/GIFs, clear post-silicon narrative, "how to run."
- **DoD:** fresh clone → one command → working demo.

---

## 9. Scope control

**Protected spine (must finish):**
generator → C++ log parser → DB → Schmoo/wafer-map analysis → minimal dashboard.

**Cut-first order if behind schedule:**
1. Report generation
2. Register compare (keep decode)
3. Docker packaging (fall back to documented manual run)

Never leave the spine half-broken to chase a rib.

---

## 10. Definition of done (project)

- [ ] One command generates realistic synthetic data.
- [ ] C++ `sep_core` module builds and is importable; parses logs + decodes registers.
- [ ] Data ingested into a relational schema; yield queries work.
- [ ] Analysis produces yield, Pareto, Schmoo, wafer-map outputs.
- [ ] Dashboard renders Schmoo plot + wafer map from live data.
- [ ] Automated PDF/HTML report generates for a lot.
- [ ] `docker compose up` runs the whole thing with seeded data.
- [ ] README tells the post-silicon story with visuals.
- [ ] Tests: pytest (Python) + at least one C++ test target; CI (stretch).

---

## 11. Stretch goals (post–2 weeks)

- STDF-style import (real ATE format literacy).
- Interactive Schmoo (hover to see failing test at each point).
- SystemRDL subset for register specs (instead of custom JSON).
- GitHub Actions CI (build C++ module, run tests, lint).
- Postgres deployment + Alembic migrations.
- Bridge to the RTL portfolio: ingest sim/coverage artifacts the RTL projects produce.

---

## 12. Learning outcomes (what you can claim)

- **C/C++:** wrote a performance-oriented streaming parser and a bit-level register decoder, exposed to Python as a compiled extension (CMake + pybind11) — real FFI, not toy code.
- **Python:** production patterns — typed, tested, packaged, ORM-backed, API-served.
- **Domain:** end-to-end post-silicon validation data pipeline; modeled realistic failure/yield behavior; Schmoo and wafer-map literacy.
- **Systems/tooling:** relational schema design, Dockerized full-stack app, Git hygiene.
