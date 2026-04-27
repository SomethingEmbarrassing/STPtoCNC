from pathlib import Path

from stptocnc.config import EmiMachineProfile


def test_emi_machine_profile_loads_from_json(tmp_path: Path) -> None:
    payload = tmp_path / "profile.json"
    payload.write_text(
        '{"post_label":"EMI TEST","trim_cut_command":"M77","torch_on_command":"M15","torch_off_command":"M16","torch_raise_command":"M25","piece_complete_prompt":"(DONE)","nested_complete_prompt":"(NEST DONE)","footer_command":"M2","wrapped_feed_mode_command":"G01 G93.1 F#777"}',
        encoding="utf-8",
    )

    profile = EmiMachineProfile.from_json_file(payload)
    assert profile.post_label == "EMI TEST"
    assert profile.trim_cut_command == "M77"
    assert profile.torch_on_command == "M15"
    assert profile.torch_off_command == "M16"
    assert profile.footer_command == "M2"
    assert profile.process_feed_ipm == 140.0
    assert profile.wrapped_step_degrees_round == 3.21429
    assert profile.wrapped_feed_mode_command == "G01 G93.1 F#777"
