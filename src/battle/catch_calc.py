"""Pure catch-probability math (Gen 3/4 formula as used by PokeMMO).

The shake/probability math is ported 1:1 from the PokeMMO Hub implementation
(src/hooks/useCatchRate.jsx, github.com/PokeMMO-Tools/pokemmo-hub). The
conditional ball multipliers are ported from the PokeMMO-specific catch
calculator (c4vv/CatchCalc, pokeballs.js). This module performs no I/O.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from battle.name_reader import NameReader
from battle.catch_chain import CatchChain

X_CAP = 255.0
SHAKE_SCALE = 65536.0

# Enemy types that the Net Ball boosts (OpenCV-agnostic; lower-cased on use).
NET_TYPES = frozenset({"water", "bug"})


@dataclass(frozen=True)
class BattleContext:
    """Everything a conditional ball rule needs about the current battle.

    `turns_completed` is 0 during the first turn (so Quick Ball is active and
    Timer Ball is x1), then 1 after the first turn resolves, etc.
    `turns_asleep` is how many turns the enemy has been asleep (Dream Ball)."""

    turns_completed: int = 0
    turns_asleep: int = 0
    enemy_asleep: bool = False  # current sleep status (Dream Ball requires it)
    enemy_types: tuple[str, ...] = ()
    enemy_level: int = 1
    dusk_active: bool = False  # night or cave (Dusk Ball condition)
    repeat_chain: int = 0  # consecutive catches of THIS species in an unbroken series (Repeat Ball)


def _quick(ctx: BattleContext) -> float:
    return 5.0 if ctx.turns_completed == 0 else 1.0


def _timer(ctx: BattleContext) -> float:
    return 1.0 + min(3.0, ctx.turns_completed * 0.3)


def _net(ctx: BattleContext) -> float:
    return 3.5 if NET_TYPES & {t.lower() for t in ctx.enemy_types} else 1.0


def _nest(ctx: BattleContext) -> float:
    return min(max(7.0 - 0.2 * (ctx.enemy_level - 1), 1.0), 4.0)


def _dusk(ctx: BattleContext) -> float:
    return 2.5 if ctx.dusk_active else 1.0


# Dream Ball by consecutive sleep turns (PokeMMO capture calculator): 0/1/2/3
# turns -> 1x / 1.5x / 2.5x / 4x; more turns stay at the 4x cap.
_DREAM_BY_SLEEP = (1.0, 1.5, 2.5, 4.0)


def _dream(ctx: BattleContext) -> float:
    # The boost only applies while the enemy is actually asleep; otherwise 1x.
    if not ctx.enemy_asleep:
        return 1.0
    return _DREAM_BY_SLEEP[min(max(ctx.turns_asleep, 0), 3)]


# Repeat Ball (PokeMMO): +0.1x for each consecutive catch of the SAME species in
# an unbroken series, starting at 1.0x and capping at 2.5x once 15 are chained
# (1.0 + 0.1*15). The chain breaks when the series is interrupted (see app.py).
_REPEAT_STEP = 0.1
_REPEAT_MAX = 2.5


def _repeat(ctx: BattleContext) -> float:
    return min(1.0 + _REPEAT_STEP * max(ctx.repeat_chain, 0), _REPEAT_MAX)


# Conditional ball rules, keyed by the "rule" field in balls.json.
BALL_RULES: dict[str, Callable[[BattleContext], float]] = {
    "quick": _quick,
    "timer": _timer,
    "net": _net,
    "nest": _nest,
    "dusk": _dusk,
    "dream": _dream,
    "repeat": _repeat,
}


def ball_multiplier(ball: dict, ctx: BattleContext) -> float:
    """Resolve a ball's catch multiplier: a flat `rate`, or a conditional
    `rule` evaluated against `ctx`."""
    if "rate" in ball:
        return float(ball["rate"])
    rule = ball.get("rule")
    if rule in BALL_RULES:
        return BALL_RULES[rule](ctx)
    raise ValueError(f"ball {ball.get('id')!r} has neither a known rule nor a rate")


def x_value(
    hp_fraction: float,
    base_catch_rate: float,
    ball_rate: float = 1.0,
    status_rate: float = 1.0,
) -> float:
    """The pre-shake quantity `x`; catch is guaranteed at x >= 255.

    `hp_fraction` is currentHP / maxHP in (0, 1]; max HP cancels out of the
    original formula, so the fraction read off the HP bar is sufficient.
    """
    if not 0.0 < hp_fraction <= 1.0:
        raise ValueError(f"hp_fraction must be in (0, 1], got {hp_fraction}")
    if base_catch_rate <= 0:
        raise ValueError(f"base_catch_rate must be positive, got {base_catch_rate}")
    return ((3.0 - 2.0 * hp_fraction) / 3.0) * base_catch_rate * ball_rate * status_rate


def catch_probability(
    hp_fraction: float,
    base_catch_rate: float,
    ball_rate: float = 1.0,
    status_rate: float = 1.0,
) -> float:
    """Probability in [0, 1] that a single throw catches (four shake checks)."""
    x = x_value(hp_fraction, base_catch_rate, ball_rate, status_rate)
    if x >= X_CAP:
        return 1.0
    y = SHAKE_SCALE / (X_CAP / x) ** 0.25
    return (y / SHAKE_SCALE) ** 4

def battle_context(
    enemy: dict,
    turns_completed: int = 0,
    turns_asleep: int = 0,
    enemy_asleep: bool = False,
    dusk_active: bool = False,
    repeat_chain: int = 0,
) -> BattleContext:
    """Build the conditional-ball context from a resolved enemy dict.

    turns_completed/turns_asleep default to 0 until the turn counter lands, so
    Quick Ball reads x5, Timer Ball x1 and Dream Ball x1 — all correct for the
    first turn with no accumulated sleep. repeat_chain is the current same-species
    catch streak (0 unless this enemy matches the active Repeat Ball chain)."""
    return BattleContext(
        turns_completed=turns_completed,
        turns_asleep=turns_asleep,
        enemy_asleep=enemy_asleep,
        enemy_types=tuple(enemy.get("types") or ()),
        enemy_level=enemy.get("level") or 1,
        dusk_active=dusk_active,
        repeat_chain=repeat_chain,
    )


def format_line(
    name: str, hp_pct: float, status: str, probs: list[tuple[str, float | None]]
) -> str:
    balls = "  ".join(f"{ball} {'??' if p is None else f'{100 * p:5.1f}%'}" for ball, p in probs)
    return f"{name:12.12s} HP {hp_pct:5.1f}% [{status}]  {balls}"


def ball_probs(
    hp_pct: float, base_rate: int | None, status_rate: float, balls: list[dict], ctx: BattleContext
) -> list[tuple[str, float | None]]:
    """Catch probability per ball. base_rate is None for species with no known
    catch rate (roaming Latias/Latios/Mesprit/Cresselia) -> every prob is None
    (the overlay/console then show "??")."""
    if base_rate is None:
        return [(b["name"], None) for b in balls]
    return [
        (
            b["name"],
            catch_probability(hp_pct / 100.0, base_rate, ball_multiplier(b, ctx), status_rate),
        )
        for b in balls
    ]


def resolve_enemy(
    species_override: dict | None,
    name_reader: NameReader | None,
    frame_bgr,
    bar,
) -> dict | None:
    """Enemy dict ({name, catch_rate, types, level}) for a bar: the override if
    given, else OCR. None when the name can't be read."""
    if species_override is not None:
        return species_override
    assert name_reader is not None
    return name_reader.read(frame_bgr, bar)


def chain_for(chain: CatchChain, enemy: dict | None) -> int:
    """The current catch chain length that applies to THIS enemy: the running
    chain if it's the same species, else 0 (Repeat Ball shows 1x for a fresh
    species)."""
    return chain.length_for(enemy.get("id") if enemy else None)
