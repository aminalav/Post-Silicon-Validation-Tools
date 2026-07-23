"""Generate realistic synthetic post-silicon validation data.

Real ATE data (STDF etc.) is proprietary/NDA-locked, so this models the
*behavior* of silicon test data instead:

* **Test measurements** with process-corner variation and limit-based binning.
* **Schmoo sweeps** (voltage x frequency) with a believable failing edge:
  a die can only reach a max frequency that scales with voltage, plus
  per-die variation and noise.
* **Wafer maps** with a systematic radial yield loss (edge dies fail more)
  layered on top of random defects.
* **Register dumps** whose bitfields encode plausible die state.

Everything is seeded for reproducibility.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Process corners shift the mean of parametric measurements.
CORNERS = ["TT", "FF", "SS", "FS", "SF"]
_CORNER_SHIFT = {"TT": 0.0, "FF": 0.6, "SS": -0.6, "FS": 0.2, "SF": -0.2}

# (name, unit, nominal, sigma, lower_limit, upper_limit)
_TEST_SPECS = [
    ("VDD_CORE", "V", 0.80, 0.015, 0.75, 0.85),
    ("IDDQ", "uA", 50.0, 12.0, 0.0, 90.0),
    ("FMAX", "GHz", 2.60, 0.18, 2.20, 3.20),
    ("LEAKAGE", "nA", 120.0, 30.0, 0.0, 220.0),
    ("TEMP_SENSOR", "C", 25.0, 1.5, 18.0, 32.0),
]

# Register spec used both to generate raw values and (elsewhere) to decode them.
# (field_name, lsb, width)
REG_SPEC = [
    ("ENABLE", 0, 1),
    ("MODE", 1, 3),
    ("VOLTAGE_TRIM", 4, 5),
    ("FREQ_DIV", 9, 4),
    ("STATUS", 13, 3),
    ("ERROR_CODE", 16, 8),
    ("REVISION", 24, 8),
]


@dataclass
class GenConfig:
    lot_id: str = "LOT001"
    product: str = "SEP-SOC-A0"
    n_wafers: int = 3
    grid: int = 12  # dies laid out on a grid x grid square, circle-masked
    seed: int = 42


def _die_grid(grid: int) -> list[tuple[int, int]]:
    """Return (x, y) positions inside the wafer circle for a grid x grid layout."""
    c = (grid - 1) / 2.0
    r = grid / 2.0
    coords = []
    for y in range(grid):
        for x in range(grid):
            if ((x - c) ** 2 + (y - c) ** 2) ** 0.5 <= r:
                coords.append((x, y))
    return coords


def _radial_health(x: int, y: int, grid: int) -> float:
    """1.0 at center, decreasing toward the edge (systematic yield loss)."""
    c = (grid - 1) / 2.0
    r = grid / 2.0
    dist = ((x - c) ** 2 + (y - c) ** 2) ** 0.5 / r
    return float(np.clip(1.0 - 0.7 * dist**2, 0.0, 1.0))


def generate(out_dir: str | Path, config: GenConfig | None = None) -> Path:
    """Generate a full synthetic lot under ``out_dir/<lot_id>/`` and return the path."""
    cfg = config or GenConfig()
    rng = np.random.default_rng(cfg.seed)

    out = Path(out_dir) / cfg.lot_id
    out.mkdir(parents=True, exist_ok=True)

    coords = _die_grid(cfg.grid)

    dies_rows = []
    test_rows = []
    schmoo_rows = []
    reg_rows = []

    for wafer in range(1, cfg.n_wafers + 1):
        for (x, y) in coords:
            die_id = f"W{wafer:02d}_X{x:02d}Y{y:02d}"
            corner = CORNERS[rng.integers(0, len(CORNERS))]
            health = _radial_health(x, y, cfg.grid)
            # A "weak" die (edge/defect) shifts parametrics and lowers fmax.
            weak = rng.random() > health

            dies_rows.append([die_id, wafer, x, y, corner])

            # --- Parametric tests ---
            die_fail = False
            fmax_val = 2.6
            for name, _unit, nom, sigma, lo, hi in _TEST_SPECS:
                shift = _CORNER_SHIFT[corner] * sigma
                penalty = (2.5 * sigma) if weak else 0.0
                if name in ("IDDQ", "LEAKAGE"):
                    val = nom + shift + rng.normal(0, sigma) + penalty
                elif name == "FMAX":
                    val = nom + shift + rng.normal(0, sigma) - penalty
                    fmax_val = val
                else:
                    val = nom + shift + rng.normal(0, sigma)
                val = round(float(val), 4)
                test_rows.append([die_id, name, val, lo, hi])
                if not (lo <= val <= hi):
                    die_fail = True

            # --- Schmoo sweep: voltage x frequency ---
            # Max reachable freq scales with voltage; edge below which it passes.
            for vi in np.linspace(0.65, 0.95, 13):
                v = round(float(vi), 3)
                fmax_at_v = (0.8 + 2.6 * (v - 0.6)) * (fmax_val / 2.6)
                for fi in np.linspace(1.0, 3.4, 13):
                    f = round(float(fi), 3)
                    margin = fmax_at_v - f + rng.normal(0, 0.05)
                    passed = int(margin > 0)
                    schmoo_rows.append([die_id, "voltage", "frequency", v, f, passed])

            # --- Register dump ---
            raw = _build_register(rng, weak, die_fail)
            reg_rows.append([die_id, "CORE_STATUS", f"0x{raw:08X}"])

            # Final bin recorded on the die row later via a second pass is
            # overkill; store bin inline instead.
            dies_rows[-1].append(_bin_of(die_fail, weak))

    _write_csv(out / "dies.csv",
               ["die_id", "wafer_number", "x", "y", "process_corner", "final_bin"],
               dies_rows)
    _write_test_log(out / "tests.log", test_rows)
    _write_csv(out / "schmoo.csv",
               ["die_id", "param_x", "param_y", "x_val", "y_val", "pass"],
               schmoo_rows)
    _write_csv(out / "registers.csv",
               ["die_id", "reg_name", "raw_value"], reg_rows)
    _write_reg_spec(out / "register_spec.csv")

    return out


def _build_register(rng: np.random.Generator, weak: bool, die_fail: bool) -> int:
    """Assemble a 32-bit register value from the field spec."""
    fields = {
        "ENABLE": 1,
        "MODE": int(rng.integers(0, 8)),
        "VOLTAGE_TRIM": int(rng.integers(8, 24)),
        "FREQ_DIV": int(rng.integers(1, 16)),
        "STATUS": 4 if not die_fail else int(rng.integers(5, 8)),
        "ERROR_CODE": 0 if not die_fail else int(rng.integers(1, 256)),
        "REVISION": 0xA0,
    }
    raw = 0
    for name, lsb, width in REG_SPEC:
        raw |= (fields[name] & ((1 << width) - 1)) << lsb
    if weak:  # nudge a status bit so weak dies look different when decoded
        raw |= 1 << 15
    return raw & 0xFFFFFFFF


def _bin_of(die_fail: bool, weak: bool) -> int:
    if not die_fail:
        return 1  # pass bin
    return 4 if weak else 2  # 4 = edge/parametric, 2 = functional fail


def _write_csv(path: Path, header: list[str], rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _write_test_log(path: Path, rows: list) -> None:
    """Write the test log in the line format the C++ parser consumes."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# die_id,test_name,value,lower_limit,upper_limit\n")
        for die_id, name, value, lo, hi in rows:
            fh.write(f"{die_id},{name},{value},{lo},{hi}\n")


def _write_reg_spec(path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "lsb", "width"])
        w.writerows([[n, lsb, width] for n, lsb, width in REG_SPEC])
