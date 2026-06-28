"""Global application timing, polling, and tuning constants.

These constants control the performance and responsiveness of the application,
including CV polling rates (Hz) and state machine grace periods.
"""

# =============================================================================
# POLLING FREQUENCIES (Hz / Frame Rates)
# =============================================================================
# These control how often the main vision loop captures and processes a frame.

WAITING_POLL_S = 2.0  # 0.5 Hz: App is waiting for the game window to appear
IDLE_FRAME_S = 0.25  # 4.0 Hz: Walking in overworld (high enough for fast encounters)
BATTLE_FRAME_S = 0.5  # 2.0 Hz: In battle (menus are static, no need to burn CPU)
DEX_LOC_INTERVAL_S = 0.25  # 4.0 Hz: How often to OCR the location HUD while walking


# =============================================================================
# BATTLE STATE TRANSITIONS (Grace Periods)
# =============================================================================
# Timeouts to prevent the state machine from dropping the battle state prematurely.

# How long the battle-specific signals (enemy bar + menu/action/catch templates)
# must ALL be gone before the battle ends. Short when the battle UI panel is
# already gone (back to the overworld -> clear the catch overlay promptly), but
# long while the dark command panel is still up: a 2-turn move (Fly/Dig/Solarbeam)
# hides the enemy bar with no menu for a couple seconds mid-battle.
BATTLE_END_GRACE_S = 1.0

# General battle animation padding.
BATTLE_ANIM_GRACE_S = 4.0

# Trainer battles cycle through several Pokemon with multi-second gaps (faint +
# "sent out") that have no battle signal; a longer grace keeps those gaps from
# ending the battle (which would flash the overlays and re-run trainer detection).
TRAINER_END_GRACE_S = 6.0

# Right after a battle starts, the previous battle's last "Turn N" can still be
# in-flight from the async chat OCR. Ignore a turn-1 chat reading only within this
# window.
BATTLE_START_GRACE_S = 3.0


# =============================================================================
# VISION & OCR DEBOUNCING
# =============================================================================

# The command menu must hold present/absent this many battle frames before the
# turn counter accepts the change — filters brief template-match flicker.
MENU_STABLE_FRAMES = 2

# The chat ("Turn N started!") is ground truth. A LOWER chat reading is only
# trusted once the menu hasn't advanced for this long, preventing stale async
# reads from dragging the count down.
TURN_DOWN_GUARD_S = 3.0

# How long the HUD location mask must remain perfectly still before OCR is allowed
# to run. Filters out blur from camera panning and rapid-fire UI transitions.
LOC_MASK_STABLE_S = 0.125


# =============================================================================
# UI & DISPLAY
# =============================================================================

# Dex entries shown before collapsing the rest into a "+X" summary
DEX_SHOWN_MAX = 5
