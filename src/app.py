"""ShakeChecker: WAITING -> IDLE -> BATTLE state machine driving the overlay.

Watches the PokeMMO window and, during a wild battle, shows per-ball catch
probabilities in a click-through overlay docked to the game window (and mirrors
them to the console as a debug log). Species, HP%, status and turn are read from
the screen; everything can be overridden from the command line:

    python src/app.py                      # auto: identify species via OCR
    python src/app.py --species Onix        # override the detected species
    python src/app.py --species Onix --status slp   # override the detection too
    python src/app.py --rate 45             # raw base catch rate instead
    python src/app.py --image fixtures/x.png  # offline: analyse one PNG (no overlay)
    python src/app.py --list-windows        # diagnose window detection
"""

from __future__ import annotations

import argparse
import enum
import io
import json
import logging
import sys
import time
from concurrent.futures import Future
from typing import Any

import numpy as np
import win32api
import win32con
import win32event
import winerror
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget

from battle.battle_log import AsyncChatReader, read_turn_number
from battle.battle_logic import (
    apply_chat_turn,
    battle_end_grace,
    debounce_battle,
    debounce_menu,
    is_horde_remnant,
    is_in_battle,
)
from ui.tray_menu import build_tray
from battle.battle_reader import (
    BattleState,
    BattleTextReader,
    Calibration,
    Status,
    is_battle_ui_present,
    is_trainer_battle,
    load_calibration,
    read_battle,
    read_caught_icon,
)

from battle.hp_settler import HpSettler
from battle.name_reader import NameReader
from battle.status_settler import StatusSettler
from battle.turn_tracker import TurnTracker
from core import paths
from core.account_store import AccountConfig, CaughtStore, delete_account_data
from core.game_time import current_game_minute, is_dusk_ball_night, season_name
from core.settings_store import Settings
from core.utils import parse_coord
from core.window_capture import (
    WINDOW_TITLE,
    WindowCapture,
    find_pokemmo_hwnd,
    fold_confusables,
    get_client_rect,
    get_window_rect,
    is_window_alive,
    iter_visible_windows,
    set_dpi_awareness,
    title_matches,
)
from dex.dex_formatters import dex_panel_text
from dex.dex_session import DexSession, LocationView
from dex.dex_tracker import EncounterData
from dex.location_reader import is_cave_location, read_location
from ui.battle_panel import BattlePanel
from ui.dex_panel import DexPanel
from ui.ui_overlay import scale_for_window

from core.app_state import (
    AREA_INDEX_PATH,
    BATTLE_ANIM_GRACE_S,
    BATTLE_END_GRACE_S,
    BATTLE_FRAME_S,
    BATTLE_START_GRACE_S,
    DATA,
    DEX_LOC_INTERVAL_S,
    DEX_SHOWN_MAX,
    ENCOUNTERS_PATH,
    IDLE_FRAME_S,
    LEGENDARIES_PATH,
    LOC_MASK_STABLE_S,
    MENU_STABLE_FRAMES,
    SPECIES_PATH,
    TEMPLATES_DIR,
    TRAINER_END_GRACE_S,
    TURN_DOWN_GUARD_S,
    USERDATA,
    WAITING_POLL_S,
    AppState,
    load_balls,
    load_status_rates,
    lookup_species,
)
from core.app_controller import AppController
from core.debug_dump import trigger_debug_dump

log = logging.getLogger("shakechecker")


class _LevelFormatter(logging.Formatter):
    """Plain message for INFO (the console output the user reads), '[dbg]'-prefixed
    for DEBUG -- preserving the exact look of the old print()s while letting the log
    level (set by --debug) decide what is shown. Tracebacks (log.exception) are kept."""

    def format(self, record: logging.LogRecord) -> str:
        msg = ("[dbg] " if record.levelno <= logging.DEBUG else "") + record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


def setup_logging(debug: bool) -> None:
    """Route the loop's events to the console, or to a log file when there is no
    console. A windowless (console=False) PyInstaller build has sys.stdout == None,
    so a StreamHandler(sys.stdout) would crash on the first log call; fall back to
    %APPDATA%/ShakeChecker/shakechecker.log so issues stay diagnosable. --debug
    raises the level to DEBUG in either case."""
    log.handlers.clear()
    log.setLevel(logging.DEBUG if debug else logging.INFO)
    log.propagate = False  # don't double-print via the root logger
    handler: logging.Handler
    if sys.stdout is not None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        try:
            logfile = paths.userdata_dir() / "shakechecker.log"
            logfile.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(logfile, mode="w", encoding="utf-8")
        except OSError:
            handler = logging.NullHandler()
    handler.setFormatter(_LevelFormatter())
    log.addHandler(handler)


def analyze_image(
    image_path: str,
    species_override: dict | None,
    status_override: str | None,
    cal: Calibration,
) -> None:
    """Offline mode: run the full pipeline on a single PNG and print the result.

    Lets you verify reader + probabilities + output format without the live
    game (same code path the live loop uses)."""
    import cv2

    frame = cv2.imread(image_path)
    if frame is None:
        raise SystemExit(f"cannot read image: {image_path!r}")
    status_rates = load_status_rates()
    balls = load_balls()
    name_reader = None if species_override else NameReader(cal.name, SPECIES_PATH)
    reading = read_battle(frame, cal)
    print(f"{image_path}")
    print(f"  state: {reading.state.value}  (bars detected: {len(reading.bars)})")
    if reading.state is BattleState.MULTI:
        print("  -> horde/double battle: ignored in v1 (overlay would stay hidden)")
    for i, bar in enumerate(reading.bars):
        status = status_override or bar.status.value
        enemy = resolve_enemy(species_override, name_reader, frame, bar)
        label = enemy["name"] if enemy else "?"
        tag = f"bar {i}: " if len(reading.bars) > 1 else ""
        print(
            f"  {tag}{label}  HP {bar.hp_pct:.1f}% ({bar.color.value})  status: {bar.status.value}"
        )
        if reading.state is BattleState.SINGLE and enemy is not None:
            turn = read_turn_number(frame, cal.chat)
            turns_completed = turn - 1 if turn else 0
            dusk = is_cave_location(read_location(frame, cal.location))
            ctx = battle_context(enemy, turns_completed=turns_completed, dusk_active=dusk)
            probs = ball_probs(bar.hp_pct, enemy["catch_rate"], status_rates[status], balls, ctx)
            turn_note = f"[turn {turn}] " if turn else "[turn ?] "
            print("  " + turn_note + format_line(label, bar.hp_pct, status, probs))


def list_windows() -> None:
    """Diagnostic: print every visible top-level window and mark PokeMMO
    matches, so window-detection problems can be seen directly."""
    set_dpi_awareness()
    windows = iter_visible_windows()
    matches = 0
    print(
        f"{len(windows)} visible top-level windows (looking for titles starting with "
        f"{WINDOW_TITLE!r}):\n"
    )
    for hwnd, title in windows:
        is_match = title_matches(title)
        rect = get_client_rect(hwnd)
        size = (
            f"{rect.width}x{rect.height} @ ({rect.left},{rect.top})" if rect else "no client rect"
        )
        mark = " <-- MATCH" if is_match else ""
        if is_match:
            matches += 1
        print(f"  hwnd={hwnd:>10}  {size:28s}  {title!r}{mark}")
        folded = fold_confusables(title)
        if is_match and folded != title:
            cps = " ".join(f"U+{ord(c):04X}" for c in title)
            print(f"             title uses non-ASCII homoglyphs; folds to {folded!r}")
            print(f"             codepoints: [{cps}]")
    picked = find_pokemmo_hwnd()
    print(f"\n{matches} title match(es). find_pokemmo_hwnd() -> {picked}")
    if picked is not None:
        print(f"  selected client rect: {get_client_rect(picked)}")


def build_dex(account_override: str | None) -> DexSession | None:
    """Build the dex session for the active account, or None if the encounter
    data is missing. The active account is chosen manually and remembered: an
    explicit --account wins, else the last used one, else a 'default' profile."""
    if not ENCOUNTERS_PATH.exists():
        log.info("dex: encounters.json not found (run scripts/update_data.py) — dex disabled")
        return None
    data = EncounterData.load(ENCOUNTERS_PATH, LEGENDARIES_PATH)

    import json

    raw_idx = json.loads(AREA_INDEX_PATH.read_text("utf-8"))
    area_index = {loc: region for region, locs in raw_idx.items() for loc in locs}

    cfg = AccountConfig.load(USERDATA)
    account = cfg.resolve_active(account_override)
    if account is None:
        account = cfg.use("default")
        log.info("dex: no account set — using 'default' (pass --account NAME per character)")
    caught = CaughtStore.for_account(USERDATA, account)
    log.info(f"dex: account '{account}' — {len(caught.caught)} species marked caught")
    return DexSession(data, caught, area_index)


SINGLE_INSTANCE_NAME = "ShakeChecker_SingleInstance_Mutex"


def acquire_single_instance(name: str = SINGLE_INSTANCE_NAME) -> int | None:
    """Acquire a process-wide lock so only ONE ShakeChecker runs at a time. Returns
    the mutex handle (the caller must keep a reference for the whole process
    lifetime) or None if another instance already holds it. A Windows named mutex is
    released by the kernel when the owning process exits -- even on a crash -- so
    there is no stale lock to clean up."""
    handle = win32event.CreateMutex(None, False, name)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        win32api.CloseHandle(handle)  # our handle is a 2nd ref to the existing mutex
        return None
    return handle


def run(
    species_override: dict | None,
    status_override: str | None,
    cal: Calibration,
    account: str | None = None,
    debug: bool = False,
) -> None:
    setup_logging(debug)
    # Only one instance may run: a second would draw a duplicate overlay over the
    # first (looks like ghosting). Hold the lock for the whole process via `lock`.
    lock = acquire_single_instance()
    if lock is None:
        log.info("ShakeChecker is already running; this instance will exit")
        win32api.MessageBox(
            0,
            "ShakeChecker is already running.",
            "ShakeChecker",
            win32con.MB_OK | win32con.MB_ICONINFORMATION,
        )
        return

    # Suppress harmless "SetProcessDpiAwarenessContext() failed" warnings.
    # We manually set DPI awareness for accurate screen capture coordinates,
    # so PyQt's later attempt fails.
    from PyQt6.QtCore import qInstallMessageHandler

    def qt_message_handler(mode, context, message):
        if "SetProcessDpiAwarenessContext" in message or "DPI_AWARENESS_CONTEXT" in message:
            return
        if "requestActivate() called for" in message and "WindowDoesNotAcceptFocus" in message:
            return
        # Pass through other messages
        import sys

        print(message, file=sys.stderr)

    qInstallMessageHandler(qt_message_handler)

    app = QApplication(sys.argv[:1])
    # The overlay and dex panels hide themselves between battles, so don't quit when
    # no window is visible -- the app lives in the tray and is quit from there.
    app.setQuitOnLastWindowClosed(False)
    icon = QIcon(str(paths.DATA_DIR / "shakechecker.ico"))
    app.setWindowIcon(icon)

    battle_panel = BattlePanel([b["name"] for b in load_balls()])
    dex = build_dex(account)
    dex_panel = DexPanel() if dex is not None else None
    loop = AppController(
        species_override, status_override, cal, battle_panel, dex=dex, dex_panel=dex_panel
    )

    # Tray presence: a windowless build has no taskbar entry, so the tray icon is how
    # the user sees it's running and how they quit it (right-click -> Quit).
    tray = build_tray(icon, app.quit, paths.APP_VERSION)

    loop.start()
    try:
        code = app.exec()
    finally:
        loop.chat.shutdown()
    sys.exit(code)


def restrict_onnx_threads() -> None:
    """Monkey-patch onnxruntime.SessionOptions to strictly use 1 thread.
    The bundled rapidocr_onnxruntime v1.2.3 hardcodes its own SessionOptions,
    defaulting to all cores. Run in a tight loop, this thrashes the CPU."""
    try:
        import onnxruntime
    except ImportError:
        return

    original_init = onnxruntime.SessionOptions.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.intra_op_num_threads = 1
        self.inter_op_num_threads = 1

    onnxruntime.SessionOptions.__init__ = patched_init


def main() -> None:
    restrict_onnx_threads()

    # Ball names contain non-ASCII (Poké Ball); force UTF-8 on the Windows console.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="ShakeChecker console output")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--species", help="override the auto-detected species, e.g. Onix")
    group.add_argument("--rate", type=int, help="override with a raw base catch rate")
    parser.add_argument(
        "--status",
        default=None,
        choices=sorted(load_status_rates()),
        help="override the auto-detected enemy status (default: read from screen)",
    )
    parser.add_argument(
        "--image",
        help="offline mode: analyze a single PNG (e.g. a fixture) instead of the live window",
    )
    parser.add_argument(
        "--list-windows",
        action="store_true",
        help="diagnostic: list visible windows and PokeMMO matches, then exit",
    )
    parser.add_argument(
        "--account",
        help="PokeMMO account/character for the dex caught-list (remembered; "
        "defaults to the last used)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="verbose turn-counter diagnostics (chat reads, menu advances)",
    )
    args = parser.parse_args()

    if args.list_windows:
        list_windows()
        return

    # species is read from the screen by default; --species/--rate override it
    species_override: dict | None = None
    if args.species is not None:
        species_override = lookup_species(args.species)
    elif args.rate is not None:
        species_override = {"name": f"rate {args.rate}", "catch_rate": args.rate, "types": []}

    cal = load_calibration(paths.CALIBRATION_PATH)

    if args.image:
        analyze_image(args.image, species_override, args.status, cal)
        return

    set_dpi_awareness()
    try:
        run(species_override, args.status, cal, account=args.account, debug=args.debug)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
