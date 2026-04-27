"""Tests for lib/display.py — pure ANSI rendering helpers."""
import pytest
from display import ansi_bg, ansi_fg, visible_len, ljust_visible, color_label

RESET = "\033[0m"

COLOR_MAP = {
    "code":   {"bg": (22, 101, 52),  "fg": (255, 255, 255)},
    "defect": {"bg": (211, 47,  47), "fg": (255, 255, 255)},
}


class TestAnsiHelpers:
    def test_ansi_bg_format(self):
        assert ansi_bg(22, 101, 52) == "\033[48;2;22;101;52m"

    def test_ansi_fg_format(self):
        assert ansi_fg(255, 255, 255) == "\033[38;2;255;255;255m"

    def test_ansi_bg_zero(self):
        assert ansi_bg(0, 0, 0) == "\033[48;2;0;0;0m"

    def test_ansi_fg_zero(self):
        assert ansi_fg(0, 0, 0) == "\033[38;2;0;0;0m"


class TestVisibleLen:
    def test_plain_string(self):
        assert visible_len("hello") == 5

    def test_empty_string(self):
        assert visible_len("") == 0

    def test_strips_simple_ansi(self):
        assert visible_len("\033[32mhello\033[0m") == 5

    def test_strips_rgb_bg_ansi(self):
        assert visible_len("\033[48;2;22;101;52mhello\033[0m") == 5

    def test_strips_multiple_codes(self):
        assert visible_len("\033[1m\033[34mhello world\033[0m") == 11

    def test_unicode_counted_correctly(self):
        assert visible_len("café") == 4

    def test_only_ansi_gives_zero(self):
        assert visible_len("\033[32m\033[0m") == 0


class TestLjustVisible:
    def test_plain_padding(self):
        assert ljust_visible("hi", 5) == "hi   "

    def test_colored_string_padded_by_visible_length(self):
        colored = "\033[32mhi\033[0m"  # visible length 2
        result = ljust_visible(colored, 5)
        assert result == colored + "   "

    def test_exact_width_no_padding(self):
        assert ljust_visible("hello", 5) == "hello"

    def test_wider_than_width_no_truncation(self):
        # Overflow — no truncation, just no padding
        result = ljust_visible("toolong", 4)
        assert result == "toolong"

    def test_zero_width(self):
        assert ljust_visible("x", 0) == "x"


class TestColorLabel:
    def test_known_label_contains_bg_escape(self):
        result = color_label("code", COLOR_MAP)
        assert "\033[48;2;" in result

    def test_known_label_contains_fg_escape(self):
        result = color_label("code", COLOR_MAP)
        assert "\033[38;2;" in result

    def test_known_label_ends_with_reset(self):
        assert color_label("code", COLOR_MAP).endswith(RESET)

    def test_known_label_contains_name(self):
        assert "code" in color_label("code", COLOR_MAP)

    def test_unknown_label_returns_plain_padded(self):
        result = color_label("unknown", COLOR_MAP)
        assert result == " unknown "
        assert "\033[" not in result

    def test_case_insensitive_lookup_applies_color(self):
        # Lookup is case-insensitive (both get colored), but display preserves original case
        assert "\033[48;2;" in color_label("Code", COLOR_MAP)
        assert "\033[48;2;" in color_label("CODE", COLOR_MAP)

    def test_case_insensitive_preserves_display_text(self):
        assert "Code" in color_label("Code", COLOR_MAP)
        assert "CODE" in color_label("CODE", COLOR_MAP)

    def test_empty_color_map_always_plain(self):
        assert color_label("code", {}) == " code "
