"""Register decode helpers built on the C++/fallback core.

The field layout lives in ``specs/core_status.csv`` (single source of truth).
"""

from __future__ import annotations

import csv
from pathlib import Path

from sep import core

DEFAULT_SPEC_PATH = Path(__file__).resolve().parent.parent / "specs" / "core_status.csv"


def load_spec_rows(path: str | Path | None = None) -> list[tuple[str, int, int]]:
    """Load (name, lsb, width) rows from a register-spec CSV."""
    path = Path(path) if path is not None else DEFAULT_SPEC_PATH
    rows: list[tuple[str, int, int]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append((row["name"], int(row["lsb"]), int(row["width"])))
    return rows


def load_spec(path: str | Path | None = None) -> list:
    """Load a register spec as core Field objects (columns: name,lsb,width)."""
    return [core.make_field(name, lsb, width) for name, lsb, width in load_spec_rows(path)]


def default_spec() -> list:
    """Field spec objects for the platform's CORE_STATUS register."""
    return load_spec()


def decode_value(raw: int, spec: list | None = None) -> list[dict]:
    """Decode a raw register value into a list of {name, value, lsb, width}."""
    spec = spec or default_spec()
    return [
        {"name": f.name, "value": int(f.value), "lsb": int(f.lsb), "width": int(f.width)}
        for f in core.decode(raw, spec)
    ]


def compare_values(expected: int, actual: int, spec: list | None = None) -> list[dict]:
    """Return fields that differ between expected and actual raw values."""
    spec = spec or default_spec()
    return [
        {"name": m.name, "expected": int(m.expected), "actual": int(m.actual)}
        for m in core.compare(expected, actual, spec)
    ]
