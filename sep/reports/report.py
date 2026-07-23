"""Generate an HTML (and optional PDF) validation report from the database."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sep import analysis, core

_TEMPLATE_DIR = Path(__file__).parent


def generate_report(
    lot_id: str,
    out_path: str | Path,
    db_url: str = "sqlite:///sep.db",
    *,
    pdf: bool = False,
) -> Path:
    """Render the validation report. Writes HTML always; PDF if ``pdf=True``.

    Returns the path actually written.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html.j2")
    html = template.render(
        lot_id=lot_id,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        backend=core.BACKEND,
        summary=analysis.yield_summary(db_url),
        pareto=analysis.failure_pareto(db_url),
    )

    out_path = Path(out_path)
    html_path = out_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")

    if pdf:
        try:
            from weasyprint import HTML  # imported lazily; heavy optional dep

            pdf_path = out_path.with_suffix(".pdf")
            HTML(string=html).write_pdf(str(pdf_path))
            return pdf_path
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "PDF export needs the 'reports' extra: pip install -e '.[reports]'"
            ) from exc

    return html_path
