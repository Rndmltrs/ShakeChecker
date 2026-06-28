from __future__ import annotations

from core.game_time import season_name
from dex.dex_structures import LocationView
from dex.dex_tracker import display_order


def dex_panel_text(view: LocationView | None) -> str:
    """The console form of the dex panel: a header with the still-needed count,
    then all rows via display_order."""
    if view is None:
        return ""
    needed = sum(1 for e in view.entries if not e.caught)
    header = (
        f"[dex] {view.route} ({view.region}) {view.period.value} {season_name(view.season)}"
        f" — {needed} needed"
    )
    rows = display_order(view.entries)
    if not rows:
        return header + "\n  (all caught here!)"
    lines = [header]
    for e in rows:
        check = " ✓" if e.caught else ""
        lines.append(f"  #{e.id:<4} {e.name} [{e.rarity}]{_ways_note(e.ways)}{check}")
    return "\n".join(lines)


def _ways_note(ways: tuple[str, ...]) -> str:
    """Parenthesised non-default encounter ways for an entry, e.g. ' (Water)',
    ' (Good Rod/Old Rod)', ' (Lure)', ' (Grass Pheno)'. Empty for plain
    grass/cave walking (dex_tracker.encounter_tag already dropped those)."""
    return f" ({'/'.join(ways)})" if ways else ""
