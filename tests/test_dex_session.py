from __future__ import annotations

from pathlib import Path

import pytest

from account_store import CaughtStore
from dex_session import DexSession
from dex_tracker import EncounterData
from game_time import Period

ROOT = Path(__file__).parent.parent
DATA = ROOT / "src" / "data"


@pytest.fixture(scope="module")
def data() -> EncounterData:
    return EncounterData.load(DATA / "encounters.json", DATA / "legendaries.json")


def make_session(data, tmp_path, period=Period.DAY, season=0) -> DexSession:
    caught = CaughtStore.for_account(tmp_path, "Tester")
    return DexSession(data, caught, period_fn=lambda: period, season_fn=lambda: season)


def test_on_location_builds_view(data, tmp_path):
    s = make_session(data, tmp_path, Period.DAY, 0)
    view = s.on_location("Viridian Forest")
    assert view is not None
    assert view.route == "VIRIDIAN FOREST"
    assert view.region == "KANTO"
    assert view.period is Period.DAY
    assert [m.id for m in view.missing] == sorted(m.id for m in view.missing)
    assert s.region == "KANTO"  # region got pinned


def test_ambiguous_location_resolves_after_region_known(data, tmp_path):
    s = make_session(data, tmp_path)
    assert s.on_location("Route 5") is None  # ambiguous, no region yet
    s.on_location("Viridian Forest")  # pins Kanto
    view = s.on_location("Route 5")
    assert view is not None and view.region == "KANTO"


def test_recording_caught_shrinks_the_missing_list(data, tmp_path):
    s = make_session(data, tmp_path, Period.DAY, 0)
    before = s.on_location("Viridian Forest").missing
    target = before[0].id
    assert s.record_caught(target) is True
    assert s.record_caught(target) is False  # already recorded
    after = s.on_location("Viridian Forest").missing
    assert target not in {m.id for m in after}
    assert len(after) == len(before) - 1


def test_caught_persists_across_sessions(data, tmp_path):
    s1 = make_session(data, tmp_path, Period.DAY, 0)
    target = s1.on_location("Viridian Forest").missing[0].id
    s1.record_caught(target)
    # a fresh session for the same account reloads the caught set from disk
    s2 = make_session(data, tmp_path, Period.DAY, 0)
    assert target not in {m.id for m in s2.on_location("Viridian Forest").missing}


def test_time_filtering_changes_the_view(data, tmp_path):
    # Viridian Forest has night-only bugs (Hoothoot, Spinarak): more at night
    day = make_session(data, tmp_path, Period.DAY, 0).on_location("Viridian Forest").missing
    night = make_session(data, tmp_path, Period.NIGHT, 0).on_location("Viridian Forest").missing
    assert len(night) > len(day)
