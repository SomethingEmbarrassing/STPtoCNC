from stptocnc.parsers.cnc_inspector import inspect_cnc_text


def test_inspect_cnc_text_finds_codes_and_prompts() -> None:
    sample = """%
(PROGRAM TEST)
G90
X1.0 Y2.0
M03
(PROMPT REMOVE PART)
M30
%"""
    result = inspect_cnc_text(sample)

    assert result["line_count"] == 8
    assert result["sections"]["operator_prompts"] == 1
    lines = result["lines"]
    assert "G90" in lines[2]["g_codes"]
    assert "M03" in lines[4]["m_codes"]
