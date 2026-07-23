"""End-to-end pipeline test: generate -> ingest -> analyze."""

from sep import analysis
from sep.datagen.generator import GenConfig, generate
from sep.db.ingest import ingest


def test_generate_ingest_analyze(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    lot = generate(tmp_path, GenConfig(lot_id="LOTX", n_wafers=2, grid=8, seed=7))

    for name in ("dies.csv", "tests.log", "schmoo.csv", "registers.csv"):
        assert (lot / name).exists()

    counts = ingest(lot, db_url)
    assert counts["wafers"] == 2
    assert counts["dies"] > 0
    assert counts["measurements"] > 0

    summary = analysis.yield_summary(db_url)
    assert summary["total_dies"] == counts["dies"]
    assert 0.0 <= summary["overall_yield_pct"] <= 100.0
    assert len(summary["per_wafer"]) == 2

    pareto = analysis.failure_pareto(db_url)
    # descending order by fail_count
    assert all(
        pareto[i]["fail_count"] >= pareto[i + 1]["fail_count"]
        for i in range(len(pareto) - 1)
    )


def test_schmoo_and_wafermap_shapes(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    lot = generate(tmp_path, GenConfig(lot_id="LOTY", n_wafers=1, grid=6, seed=3))
    ingest(lot, db_url)

    wmap = analysis.wafer_map(1, db_url)
    assert wmap["wafer_number"] == 1
    assert len(wmap["dies"]) > 0

    die_id = wmap["dies"] and _first_die_id(db_url)
    schmoo = analysis.schmoo_matrix(die_id, db_url)
    assert len(schmoo["x_vals"]) > 0
    assert len(schmoo["z"]) == len(schmoo["y_vals"])


def _first_die_id(db_url: str) -> str:
    from sqlalchemy import select

    from sep.db.models import Die, get_engine, get_session

    with get_session(get_engine(db_url)) as session:
        return session.scalars(select(Die)).first().die_id
