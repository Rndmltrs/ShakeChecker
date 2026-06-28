from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from battle.battle_log import AsyncChatReader
from battle.battle_reader import BattleTextReader
from battle.catch_chain import CatchChain
from battle.hp_settler import HpSettler
from battle.name_reader import NameReader
from battle.status_settler import StatusSettler
from battle.turn_tracker import TurnTracker


@dataclass(frozen=True)
class OcrServices:
    """Groups the low-level OCR readers into a single injectable dependency."""

    name_reader: NameReader | None
    battle_text_reader: BattleTextReader
    chat_reader: AsyncChatReader


@dataclass(frozen=True)
class BattleServices:
    """Groups the stateful battle trackers into a single injectable dependency."""

    turns: TurnTracker
    hp: HpSettler
    status: StatusSettler
    chain: CatchChain


@dataclass(frozen=True)
class AppConfig:
    """Application-wide tuning constants, timings, and configuration."""

    # --- Battle Timings ---
    turn_down_guard_s: float  # Seconds to ignore menu flashes immediately after an action
    battle_start_grace_s: float  # Seconds to wait for battle intro animations before reading name
    menu_stable_frames: int  # Consecutive frames the menu must be present to be considered stable
    horde_enemy_count: int  # Number of enemies that constitute a horde battle

    # --- Battle Boundary Grace Periods ---
    battle_anim_grace_s: float  # Seconds to wait during attack animations before ending battle
    trainer_end_grace_s: float  # Seconds to wait during trainer battle fade-out
    battle_end_grace_s: float  # Seconds to wait during wild battle fade-out

    # --- Overworld Timings ---
    dex_loc_interval_s: float  # Minimum seconds between reading the overworld location HUD
    loc_mask_stable_s: (
        float  # Seconds the location HUD must remain stable before reading (ignores fading)
    )

    # --- Frame Limits ---
    idle_frame_s: float  # Main loop sleep interval while in the overworld
    battle_frame_s: float  # Main loop sleep interval while actively in a battle
    waiting_poll_s: float  # Loop sleep interval while waiting for the game window to be found

    # --- Storage ---
    userdata_path: Path  # Path to local user data/profiles directory
