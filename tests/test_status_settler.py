from __future__ import annotations

from battle.status_settler import StatusSettler


def test_first_reading_commits_immediately():
    s = StatusSettler(stable_needed=4)
    assert s.update("psn") == "psn"


def test_brief_blip_is_ignored():
    s = StatusSettler(stable_needed=4)
    s.update("psn")
    # a few FRZ frames from the catch animation, fewer than the threshold
    assert s.update("frz") == "psn"
    assert s.update("frz") == "psn"
    assert s.update("frz") == "psn"
    # back to the real status
    assert s.update("psn") == "psn"


def test_sustained_change_takes_over():
    s = StatusSettler(stable_needed=4)
    s.update("none")  # Fully committed to "none" (count=4)

    # It takes 4 frames to drain the old confidence down to 0,
    # which swaps the candidate to "psn" with count=1.
    for _ in range(4):
        assert s.update("psn") == "none"

    # It then takes 3 more frames to build the new candidate up to count=4.
    for _ in range(2):
        assert s.update("psn") == "none"
    assert s.update("psn") == "psn"  # 7th consecutive -> switch!


def test_interrupted_candidate_resets():
    s = StatusSettler(stable_needed=3)
    s.update("psn")  # committed="psn", candidate="psn", count=3

    # 1. Start a run of "frz", draining the count
    s.update("frz")  # count -> 2
    s.update("frz")  # count -> 1

    # 2. Interruption! The original status appears again.
    s.update("psn")  # builds the "psn" count back up to 2

    # 3. Because we were interrupted, "frz" didn't even become the candidate.
    # It will take the full 3 frames to drain "psn", plus 2 more frames to build "frz".
    s.update("frz")  # psn count -> 1
    s.update("frz")  # psn count -> 0, swaps candidate to frz, frz count -> 1
    s.update("frz")  # frz count -> 2
    assert s.update("frz") == "frz"  # frz count -> 3, switch!


def test_reset_clears_state():
    s = StatusSettler(stable_needed=2)
    s.update("psn")
    s.reset()
    assert s.update("slp") == "slp"  # next battle commits fresh
