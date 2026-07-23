"""Register decode helpers built on the C++/fallback core."""

from __future__ import annotations

import csv
from pathlib import Path

from sep import core
from sep.datagen.generator import REG_SPEC


def default_spec() -> list:
    """Field spec objects for the platform's CORE_STATUS register."""
    return [core.make_field(name, lsb, width) for name, lsb, width in REG_SPEC]


def load_spec(path: str | Path) -> list:
    """Load a register spec CSV (columns: name,lsb,width)."""
    fields = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fields.append(
                core.make_field(row["name"], int(row["lsb"]), int(row["width"]))
            )
    return fields


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
