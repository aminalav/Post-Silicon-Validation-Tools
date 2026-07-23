"""Core parsing/decoding interface.

Prefers the compiled C++ extension ``sep_core`` (built via CMake + pybind11).
If it is not available (e.g. the C++ toolchain has not run yet), transparently
falls back to a pure-Python implementation with the *same* interface so the
rest of the pipeline is never blocked.

Check which backend is active at runtime via :data:`BACKEND`.
"""

from __future__ import annotations

from dataclasses import dataclass

BACKEND: str


@dataclass
class TestRecord:
    die_id: str
    test_name: str
    value: float
    lower_limit: float
    upper_limit: float
    pass_: bool


@dataclass
class DecodedField:
    name: str
    value: int
    lsb: int
    width: int


@dataclass
class FieldMismatch:
    name: str
    expected: int
    actual: int


try:  # Prefer the compiled extension.
    import sep_core as _c

    BACKEND = "cpp"

    def parse_log(path: str) -> list:
        return _c.parse_log(path)

    def parse_log_string(contents: str) -> list:
        return _c.parse_log_string(contents)

    def make_field(name: str, lsb: int, width: int):
        return _c.Field(name, lsb, width)

    def decode(raw: int, spec: list) -> list:
        return _c.decode(raw, spec)

    def compare(expected: int, actual: int, spec: list) -> list:
        return _c.compare(expected, actual, spec)

except ImportError:  # Pure-Python fallback.
    BACKEND = "python"

    @dataclass
    class Field:
        name: str
        lsb: int
        width: int

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
            out.append(
                TestRecord(die_id, test_name, v, lo_f, hi_f, lo_f <= v <= hi_f)
            )
        return out

    def parse_log(path: str) -> list[TestRecord]:
        with open(path, encoding="utf-8") as fh:
            return _parse_lines(fh)

    def parse_log_string(contents: str) -> list[TestRecord]:
        return _parse_lines(contents.splitlines())

    def make_field(name: str, lsb: int, width: int) -> "Field":
        return Field(name, lsb, width)

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
