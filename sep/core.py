"""Core parsing/decoding interface.

Prefers the compiled C++ extension ``sep_core`` (built via CMake + pybind11).
If it is not available (e.g. the C++ toolchain has not run yet), transparently
falls back to the pure-Python implementation in :mod:`sep._pyfallback`, which
exposes the *same* interface so the rest of the pipeline is never blocked.

Check which backend is active at runtime via :data:`BACKEND`.
"""

from __future__ import annotations

from sep._types import DecodedField, Field, FieldMismatch, TestRecord

__all__ = [
    "BACKEND",
    "TestRecord",
    "DecodedField",
    "FieldMismatch",
    "Field",
    "parse_log",
    "parse_log_string",
    "make_field",
    "decode",
    "compare",
]

BACKEND: str

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

except ImportError:  # Pure-Python fallback (identical interface).
    from sep import _pyfallback as _py

    BACKEND = "python"

    parse_log = _py.parse_log
    parse_log_string = _py.parse_log_string
    make_field = _py.make_field
    decode = _py.decode
    compare = _py.compare
