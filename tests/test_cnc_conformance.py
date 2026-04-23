from pathlib import Path

from stptocnc.parsers import compare_cnc_conformance


def test_compare_cnc_conformance_flags_mismatch(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.cnc"
    generated = tmp_path / "generated.cnc"
    accepted.write_text("%\n(PROGRAM A)\n(POST EMI)\nG90\nM15\nM30\n%\n", encoding="utf-8")
    generated.write_text("%\n(PROGRAM B)\n(POST EMI)\nG90\nM30\n%\n", encoding="utf-8")

    result = compare_cnc_conformance(generated, accepted)
    assert result["status"] == "needs_review"
    assert "M15" in result["count_mismatches"]

