"""Pure-Python implementation of the parsing/decoding core.

This mirrors the C++ ``sep_core`` extension exactly, one function at a time.
It is used automatically by :mod:`sep.core` when the compiled module is not
available — and it is importable on its own (``sep._pyfallback``) so you can
compare it directly against the C++ version (see
``learn/01_cpp_vs_python_parser.py``).
"""

from __future__ import annotations

from sep._types import DecodedField, Field, FieldMismatch, TestRecord


def make_field(name: str, lsb: int, width: int) -> Field:
    return Field(name, lsb, width)


def _parse_lines(lines) -> list[TestRecord]:
    out: list[TestRecord] = []
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            raise ValueError(f"malformed line {lineno}: expected 5 fields")
        die_id, test_name, value, lo, hi = parts[:5]
        v, lo_f, hi_f = float(value), float(lo), float(hi)
        out.append(TestRecord(die_id, test_name, v, lo_f, hi_f, lo_f <= v <= hi_f))
    return out


def parse_log(path: str) -> list[TestRecord]:
    with open(path, encoding="utf-8") as fh:
        return _parse_lines(fh)


def parse_log_string(contents: str) -> list[TestRecord]:
    return _parse_lines(contents.splitlines())


def _extract(raw: int, lsb: int, width: int) -> int:
    if not 1 <= width <= 64:
        raise ValueError("field width must be in 1..64")
    if lsb + width > 64:
        raise ValueError("field exceeds 64-bit register bounds")
    mask = (1 << width) - 1
    return (raw >> lsb) & mask


def decode(raw: int, spec: list) -> list[DecodedField]:
    return [
        DecodedField(f.name, _extract(raw, f.lsb, f.width), f.lsb, f.width)
        for f in spec
    ]


def compare(expected: int, actual: int, spec: list) -> list[FieldMismatch]:
    diffs: list[FieldMismatch] = []
    for f in spec:
        e = _extract(expected, f.lsb, f.width)
        a = _extract(actual, f.lsb, f.width)
        if e != a:
            diffs.append(FieldMismatch(f.name, e, a))
    return diffs
