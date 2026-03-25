from stptocnc.post.emi_writer import emit_minimal_sample


def test_emit_minimal_sample_contains_program_id() -> None:
    output = emit_minimal_sample(program_id="P100")
    assert "PROGRAM P100" in output
    assert "POST EMI 2400 PROMPTS ROP V1.4" in output
