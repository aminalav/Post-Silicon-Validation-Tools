"""Tests for the parsing/decoding core (works with either backend)."""

from sep import core


def test_backend_reports_valid_value():
    assert core.BACKEND in {"cpp", "python"}


def test_parse_log_string_computes_pass_fail():
    text = """# header
D1,VDD,0.80,0.75,0.85
D1,IDDQ,95.0,0.0,90.0

D2,VDD,0.70,0.75,0.85
"""
    records = core.parse_log_string(text)
    assert len(records) == 3
    by = {(r.die_id, r.test_name): r for r in records}
    assert by[("D1", "VDD")].pass_ is True
    assert by[("D1", "IDDQ")].pass_ is False  # over upper limit
    assert by[("D2", "VDD")].pass_ is False  # under lower limit


def test_decode_extracts_bitfields():
    spec = [
        core.make_field("ENABLE", 0, 1),
        core.make_field("MODE", 1, 3),
        core.make_field("REVISION", 24, 8),
    ]
    # ENABLE=1, MODE=5 (0b101), REVISION=0xA0
    raw = (1 << 0) | (5 << 1) | (0xA0 << 24)
    fields = {f.name: f.value for f in core.decode(raw, spec)}
    assert fields["ENABLE"] == 1
    assert fields["MODE"] == 5
    assert fields["REVISION"] == 0xA0


def test_compare_flags_only_differences():
    spec = [core.make_field("A", 0, 4), core.make_field("B", 4, 4)]
    diffs = core.compare(0x12, 0x1F, spec)  # low nibble 2 vs F; high nibble 1 vs 1
    assert len(diffs) == 1
    assert diffs[0].name == "A"
    assert diffs[0].expected == 0x2
    assert diffs[0].actual == 0xF
