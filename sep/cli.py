"""Command-line interface for the Silicon Engineering Platform.

Examples:
    sep generate --out data                 # create synthetic lot
    sep ingest data/LOT001                   # load it into the DB
    sep report LOT001 --out reports/LOT001   # write an HTML report
    sep serve                                # run the API
    sep info                                 # show active C++/Python backend
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="Silicon Engineering Platform CLI")


@app.command()
def info() -> None:
    """Show which parsing backend (C++ extension vs. Python fallback) is active."""
    from sep import core

    typer.echo(f"core backend: {core.BACKEND}")


@app.command()
def generate(
    out: str = typer.Option("data", help="output directory"),
    lot_id: str = typer.Option("LOT001", help="lot identifier"),
    product: str = typer.Option("SEP-SOC-A0", help="product name"),
    wafers: int = typer.Option(3, help="number of wafers"),
    grid: int = typer.Option(12, help="die grid size"),
    seed: int = typer.Option(42, help="RNG seed"),
) -> None:
    """Generate a synthetic post-silicon data lot."""
    from sep.datagen.generator import GenConfig
    from sep.datagen.generator import generate as gen

    path = gen(
        out,
        GenConfig(lot_id=lot_id, product=product, n_wafers=wafers, grid=grid, seed=seed),
    )
    typer.echo(f"generated lot at {path}")


@app.command()
def ingest(
    lot_dir: str = typer.Argument(..., help="path to a generated lot directory"),
    db_url: str = typer.Option("sqlite:///sep.db", help="database URL"),
) -> None:
    """Load a generated lot into the database."""
    from sep.db.ingest import ingest as do_ingest

    counts = do_ingest(lot_dir, db_url)
    typer.echo(json.dumps(counts, indent=2))


@app.command()
def yields(db_url: str = typer.Option("sqlite:///sep.db", help="database URL")) -> None:
    """Print yield summary (sanity check)."""
    from sep import analysis

    typer.echo(json.dumps(analysis.yield_summary(db_url), indent=2))


@app.command()
def report(
    lot_id: str = typer.Argument(..., help="lot identifier for the report header"),
    out: str = typer.Option("reports/report", help="output path (no extension)"),
    db_url: str = typer.Option("sqlite:///sep.db", help="database URL"),
    pdf: bool = typer.Option(False, help="also render a PDF (needs [reports] extra)"),
) -> None:
    """Generate an HTML/PDF validation report."""
    from sep.reports import generate_report

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    path = generate_report(lot_id, out, db_url, pdf=pdf)
    typer.echo(f"wrote {path}")


@app.command()
def decode(
    raw: str = typer.Argument(..., help="raw register value, e.g. 0xA000830D"),
) -> None:
    """Decode a raw CORE_STATUS register value into named fields."""
    from sep import registers

    value = int(raw, 0)
    for f in registers.decode_value(value):
        typer.echo(f"  {f['name']:<14} [{f['lsb']}:+{f['width']}] = {f['value']}")


@app.command("compare")
def compare_cmd(
    expected: str = typer.Argument(..., help="expected raw value"),
    actual: str = typer.Argument(..., help="actual raw value"),
) -> None:
    """Compare expected vs actual CORE_STATUS values field-by-field."""
    from sep import registers

    exp, act = int(expected, 0), int(actual, 0)
    mismatches = registers.compare_values(exp, act)
    if not mismatches:
        typer.echo("match: all fields equal")
        return
    typer.echo(f"mismatches ({len(mismatches)}):")
    for m in mismatches:
        typer.echo(f"  {m['name']:<14} expected={m['expected']} actual={m['actual']}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="bind host"),
    port: int = typer.Option(8000, help="bind port"),
) -> None:
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run("sep.api.app:app", host=host, port=port, reload=False)


@app.command()
def demo(
    out: str = typer.Option("data", help="data output directory"),
    db_url: str = typer.Option("sqlite:///sep.db", help="database URL"),
) -> None:
    """One-shot: generate -> ingest -> report (great for a fresh clone)."""
    from sep.datagen.generator import GenConfig
    from sep.datagen.generator import generate as gen
    from sep.db.ingest import ingest as do_ingest
    from sep.reports import generate_report

    path = gen(out, GenConfig())
    typer.echo(f"generated {path}")
    counts = do_ingest(path, db_url)
    typer.echo(f"ingested {counts}")
    Path("reports").mkdir(exist_ok=True)
    html = generate_report(path.name, "reports/report", db_url, pdf=False)
    typer.echo(f"report at {html}")
    try:
        pdf_path = generate_report(path.name, "reports/report", db_url, pdf=True)
        typer.echo(f"pdf at {pdf_path}")
    except RuntimeError as exc:
        typer.echo(f"pdf skipped: {exc}")


if __name__ == "__main__":
    app()
