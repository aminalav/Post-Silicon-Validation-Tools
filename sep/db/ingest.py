"""Ingest generated synthetic data into the relational database.

The test log is parsed via :mod:`sep.core`, which prefers the compiled C++
extension (falling back to pure Python) — keeping the C++ core on the
critical data path.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select

from sep import core
from sep.db.models import (
    Base,
    Die,
    Lot,
    Measurement,
    RegDump,
    SchmooPoint,
    Test,
    Wafer,
    get_engine,
    get_session,
)


def ingest(lot_dir: str | Path, db_url: str = "sqlite:///sep.db", *, reset: bool = True) -> dict:
    """Load one generated lot directory into the DB. Returns a summary dict."""
    lot_dir = Path(lot_dir)
    engine = get_engine(db_url)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    counts = {"wafers": 0, "dies": 0, "tests": 0, "measurements": 0,
              "schmoo": 0, "reg_dumps": 0}

    with get_session(engine) as session:
        lot = Lot(lot_id=lot_dir.name, product="SEP-SOC-A0")
        session.add(lot)
        session.flush()

        wafer_map: dict[int, Wafer] = {}
        die_map: dict[str, Die] = {}

        # --- dies.csv -> wafers + dies ---
        for row in _read_csv(lot_dir / "dies.csv"):
            wnum = int(row["wafer_number"])
            wafer = wafer_map.get(wnum)
            if wafer is None:
                wafer = Wafer(lot_pk=lot.id, wafer_number=wnum)
                session.add(wafer)
                session.flush()
                wafer_map[wnum] = wafer
                counts["wafers"] += 1
            die = Die(
                die_id=row["die_id"],
                wafer_pk=wafer.id,
                x=int(row["x"]),
                y=int(row["y"]),
                process_corner=row["process_corner"],
                final_bin=int(row["final_bin"]),
            )
            session.add(die)
            die_map[die.die_id] = die
            counts["dies"] += 1
        session.flush()

        # --- tests.log -> tests + measurements (via C++/fallback parser) ---
        test_map: dict[str, Test] = {}
        records = core.parse_log(str(lot_dir / "tests.log"))
        for rec in records:
            test = test_map.get(rec.test_name)
            if test is None:
                test = Test(
                    name=rec.test_name,
                    lower_limit=rec.lower_limit,
                    upper_limit=rec.upper_limit,
                )
                session.add(test)
                session.flush()
                test_map[rec.test_name] = test
                counts["tests"] += 1
            session.add(
                Measurement(
                    die_pk=die_map[rec.die_id].id,
                    test_pk=test.id,
                    value=rec.value,
                    passed=bool(rec.pass_),
                )
            )
            counts["measurements"] += 1

        # --- schmoo.csv ---
        for row in _read_csv(lot_dir / "schmoo.csv"):
            session.add(
                SchmooPoint(
                    die_pk=die_map[row["die_id"]].id,
                    param_x=row["param_x"],
                    param_y=row["param_y"],
                    x_val=float(row["x_val"]),
                    y_val=float(row["y_val"]),
                    passed=bool(int(row["pass"])),
                )
            )
            counts["schmoo"] += 1

        # --- registers.csv ---
        for row in _read_csv(lot_dir / "registers.csv"):
            session.add(
                RegDump(
                    die_pk=die_map[row["die_id"]].id,
                    reg_name=row["reg_name"],
                    raw_value=int(row["raw_value"], 16),
                )
            )
            counts["reg_dumps"] += 1

        session.commit()

    return counts


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def yield_by_wafer(db_url: str = "sqlite:///sep.db") -> list[dict]:
    """Quick sanity query: pass yield per wafer (final_bin == 1 is pass)."""
    engine = get_engine(db_url)
    with get_session(engine) as session:
        rows = []
        for wafer in session.scalars(select(Wafer)).all():
            dies = wafer.dies
            total = len(dies)
            passed = sum(1 for d in dies if d.final_bin == 1)
            rows.append(
                {
                    "wafer_number": wafer.wafer_number,
                    "total": total,
                    "passed": passed,
                    "yield_pct": round(100.0 * passed / total, 2) if total else 0.0,
                }
            )
        return rows
