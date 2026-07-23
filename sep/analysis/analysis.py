"""Analysis functions returning tidy structures the API/reports serve directly.

Uses pandas over SQL for readable, testable aggregations.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, text

from sep.db.models import get_engine

# Human-readable bin names for reporting.
BIN_NAMES = {1: "Pass", 2: "Functional fail", 4: "Edge/parametric fail"}


def _engine(db_url: str) -> Engine:
    return get_engine(db_url)


def yield_summary(db_url: str = "sqlite:///sep.db") -> dict:
    """Overall + per-wafer yield and bin breakdown."""
    eng = _engine(db_url)
    dies = pd.read_sql("SELECT * FROM die", eng)
    wafers = pd.read_sql("SELECT id, wafer_number FROM wafer", eng)
    dies = dies.merge(wafers, left_on="wafer_pk", right_on="id", suffixes=("", "_w"))

    total = len(dies)
    passed = int((dies["final_bin"] == 1).sum())

    per_wafer = (
        dies.groupby("wafer_number")
        .agg(total=("die_id", "count"), passed=("final_bin", lambda s: int((s == 1).sum())))
        .reset_index()
    )
    per_wafer["yield_pct"] = (100.0 * per_wafer["passed"] / per_wafer["total"]).round(2)

    bin_counts = dies["final_bin"].value_counts().sort_index()
    bins = [
        {"bin": int(b), "name": BIN_NAMES.get(int(b), f"Bin {b}"), "count": int(c)}
        for b, c in bin_counts.items()
    ]

    return {
        "total_dies": total,
        "passed": passed,
        "overall_yield_pct": round(100.0 * passed / total, 2) if total else 0.0,
        "per_wafer": per_wafer.to_dict(orient="records"),
        "bins": bins,
    }


def failure_pareto(db_url: str = "sqlite:///sep.db") -> list[dict]:
    """Failing-measurement counts per test, descending (Pareto)."""
    eng = _engine(db_url)
    df = pd.read_sql(
        "SELECT t.name AS test_name, m.passed "
        "FROM measurement m JOIN test t ON t.id = m.test_pk",
        eng,
    )
    fails = df[~df["passed"].astype(bool)]
    counts = fails.groupby("test_name").size().sort_values(ascending=False)
    total_fails = int(counts.sum())
    out = []
    cum = 0
    for name, c in counts.items():
        cum += int(c)
        out.append(
            {
                "test_name": name,
                "fail_count": int(c),
                "cum_pct": round(100.0 * cum / total_fails, 2) if total_fails else 0.0,
            }
        )
    return out


def schmoo_matrix(die_id: str, db_url: str = "sqlite:///sep.db") -> dict:
    """Pass/fail matrix for one die's Schmoo sweep (voltage x frequency)."""
    eng = _engine(db_url)
    with eng.connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT s.x_val, s.y_val, s.passed FROM schmoo s "
                "JOIN die d ON d.id = s.die_pk WHERE d.die_id = :die_id"
            ),
            conn,
            params={"die_id": die_id},
        )
    if df.empty:
        return {"die_id": die_id, "x_vals": [], "y_vals": [], "z": []}
    pivot = df.pivot_table(index="y_val", columns="x_val", values="passed", aggfunc="max")
    pivot = pivot.sort_index(ascending=False)  # high freq at top
    return {
        "die_id": die_id,
        "param_x": "voltage",
        "param_y": "frequency",
        "x_vals": [float(v) for v in pivot.columns],
        "y_vals": [float(v) for v in pivot.index],
        "z": pivot.astype(int).values.tolist(),
    }


def wafer_map(wafer_number: int, db_url: str = "sqlite:///sep.db") -> dict:
    """Per-die final-bin grid for one wafer."""
    eng = _engine(db_url)
    with eng.connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT d.x, d.y, d.final_bin FROM die d "
                "JOIN wafer w ON w.id = d.wafer_pk WHERE w.wafer_number = :wnum"
            ),
            conn,
            params={"wnum": int(wafer_number)},
        )
    return {
        "wafer_number": wafer_number,
        "dies": df.to_dict(orient="records"),
    }
