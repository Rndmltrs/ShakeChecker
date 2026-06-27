"""Catch display for species with no known catch rate (roaming Latias/Latios/
Mesprit/Cresselia have catch_rate=None). The probabilities must be None and the
console line must render "??" instead of crashing on the missing rate."""

from __future__ import annotations

from app import ball_probs, format_line
from battle.catch_calc import BattleContext

BALLS = [{"name": "Poke", "rate": 1}, {"name": "Great", "rate": 1.5}]


def test_ball_probs_unknown_rate_is_all_none():
    out = ball_probs(100.0, None, 1.0, BALLS, BattleContext())
    assert out == [("Poke", None), ("Great", None)]


def test_ball_probs_known_rate_still_computes():
    out = ball_probs(100.0, 45, 1.0, BALLS, BattleContext())
    assert [n for n, _ in out] == ["Poke", "Great"]
    assert all(p is not None and 0.0 <= p <= 1.0 for _, p in out)


def test_format_line_renders_question_marks_for_unknown():
    line = format_line("Latias", 100.0, "none", [("Poke", None), ("Great", None)])
    assert "Poke ??" in line
    assert "Great ??" in line


def test_format_line_renders_percent_for_known():
    line = format_line("Bulbasaur", 100.0, "none", [("Poke", 0.1)])
    assert "10.0%" in line

