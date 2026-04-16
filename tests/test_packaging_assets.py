from pathlib import Path

from stptocnc.gui_entry import main as gui_main


def test_gui_entrypoint_importable() -> None:
    assert callable(gui_main)


def test_packaging_assets_exist() -> None:
    root = Path(".")
    assert (root / "packaging" / "pyinstaller" / "stptocnc_gui.spec").exists()
    assert (root / "packaging" / "inno" / "stptocnc_installer.iss").exists()
    assert (root / "packaging" / "tools" / "build_exe.py").exists()
    assert (root / "packaging" / "tools" / "build_installer.py").exists()


def test_readme_contains_packaging_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "python packaging/tools/build_exe.py --clean" in readme
    assert "python packaging/tools/build_installer.py --iscc" in readme
