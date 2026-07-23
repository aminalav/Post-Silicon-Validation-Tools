"""Plain Python data types shared by both core backends.

The compiled C++ extension (``sep_core``) returns its own pybind11-bound
classes with matching attribute names; these dataclasses are the pure-Python
equivalents used by :mod:`sep._pyfallback`.
"""

from __future__ import annotations

from dataclasses import dataclass


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


@dataclass
class Field:
    name: str
    lsb: int
    width: int
