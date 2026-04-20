from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.nesting import trim_cut_for_last_piece


def test_stock_default_selection_by_profile_family() -> None:
    defaults = NestingDefaults()

    assert defaults.stock_length_for(ProfileFamily.PIPE) == 252.0
    assert defaults.stock_length_for(ProfileFamily.HSS) == 240.0
    assert defaults.stock_length_for(ProfileFamily.ANGLE) == 240.0


def test_trim_cut_rule_helper_behavior() -> None:
    defaults = NestingDefaults()

    assert trim_cut_for_last_piece("cope", defaults) == 0.25
    assert trim_cut_for_last_piece("fishmouth", defaults) == 0.25
    assert trim_cut_for_last_piece("flat", defaults) == 0.0
