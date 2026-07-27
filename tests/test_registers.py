"""Tests for register helpers, lot metadata, and expected/actual compare."""

from sqlalchemy import select

from sep import core, registers
from sep.datagen.generator import GenConfig, generate
from sep.db.ingest import ingest
from sep.db.models import Lot, RegDump, get_engine, get_session


def test_compare_values_wrapper():
    spec = [core.make_field("A", 0, 4), core.make_field("B", 4, 4)]
    diffs = registers.compare_values(0x12, 0x1F, spec)
    assert len(diffs) == 1
    assert diffs[0]["name"] == "A"
    assert diffs[0]["expected"] == 0x2
    assert diffs[0]["actual"] == 0xF


def test_lot_meta_and_expected_registers(tmp_path):
    db_url = f"sqlite:///{tmp_path / 't.db'}"
    lot = generate(
        tmp_path,
        GenConfig(lot_id="LOTZ", product="SEP-SOC-B0", n_wafers=1, grid=6, seed=1),
    )
    assert (lot / "lot.json").exists()
    assert "expected_value" in (lot / "registers.csv").read_text(encoding="utf-8").splitlines()[0]

    counts = ingest(lot, db_url)
    assert counts["reg_dumps"] > 0

    engine = get_engine(db_url)
    with get_session(engine) as session:
        row = session.scalars(select(Lot)).first()
        assert row.lot_id == "LOTZ"
        assert row.product == "SEP-SOC-B0"
        dump = session.scalars(select(RegDump)).first()
        assert dump.expected_value is not None
        mismatches = registers.compare_values(dump.expected_value, dump.raw_value)
        # Either match or structured mismatches — both are valid outcomes.
        assert isinstance(mismatches, list)
