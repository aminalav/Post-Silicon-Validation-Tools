"""REST API for the Silicon Engineering Platform dashboard.

Run with:  uvicorn sep.api.app:app --reload
The database URL is read from the SEP_DB_URL env var (default sqlite:///sep.db).
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from sep import analysis
from sep import registers as reg
from sep.db.models import Die, RegDump, Wafer, get_engine, get_session

DB_URL = os.environ.get("SEP_DB_URL", "sqlite:///sep.db")

app = FastAPI(title="Silicon Engineering Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    from sep import core

    return {"status": "ok", "core_backend": core.BACKEND}


@app.get("/api/wafers")
def wafers() -> list[dict]:
    engine = get_engine(DB_URL)
    with get_session(engine) as session:
        return [
            {"wafer_number": w.wafer_number, "die_count": len(w.dies)}
            for w in session.scalars(select(Wafer)).all()
        ]


@app.get("/api/yield")
def yield_summary() -> dict:
    return analysis.yield_summary(DB_URL)


@app.get("/api/pareto")
def pareto() -> list[dict]:
    return analysis.failure_pareto(DB_URL)


@app.get("/api/wafermap/{wafer_number}")
def wafermap(wafer_number: int) -> dict:
    return analysis.wafer_map(wafer_number, DB_URL)


@app.get("/api/schmoo/{die_id}")
def schmoo(die_id: str) -> dict:
    data = analysis.schmoo_matrix(die_id, DB_URL)
    if not data["x_vals"]:
        raise HTTPException(status_code=404, detail=f"no schmoo data for die {die_id}")
    return data


@app.get("/api/dies")
def dies(wafer_number: int | None = None, limit: int = 100) -> list[dict]:
    engine = get_engine(DB_URL)
    with get_session(engine) as session:
        stmt = select(Die)
        if wafer_number is not None:
            stmt = stmt.join(Wafer).where(Wafer.wafer_number == wafer_number)
        rows = session.scalars(stmt.limit(limit)).all()
        return [
            {
                "die_id": d.die_id,
                "x": d.x,
                "y": d.y,
                "process_corner": d.process_corner,
                "final_bin": d.final_bin,
            }
            for d in rows
        ]


@app.get("/api/registers/{die_id}")
def registers(die_id: str) -> dict:
    engine = get_engine(DB_URL)
    with get_session(engine) as session:
        die = session.scalar(select(Die).where(Die.die_id == die_id))
        if die is None:
            raise HTTPException(status_code=404, detail=f"unknown die {die_id}")
        dump = session.scalar(select(RegDump).where(RegDump.die_pk == die.id))
        if dump is None:
            raise HTTPException(status_code=404, detail="no register dump")
        return {
            "die_id": die_id,
            "reg_name": dump.reg_name,
            "raw_value": f"0x{dump.raw_value:08X}",
            "fields": reg.decode_value(dump.raw_value),
        }
