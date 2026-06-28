import enum
import logging

from battle.battle_logic import battle_end_grace, debounce_battle, is_in_battle
from core.services import AppConfig
from core.vision_controller import VisionUpdate

log = logging.getLogger("shakechecker")


class BattleDetectorState(enum.Enum):
    IDLE = "idle"
    GAP = "gap"
    ACTIVE = "active"


class BattleDetector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._battle_debounce: int = 0
        self._stable_in_battle: bool = False
        self._last_seen_battle: float = 0.0

        self._battle_overlay_brightness: float | None = None
        self._was_ui_present: bool = False

    def step(
        self,
        vision: VisionUpdate,
        needs_reading: bool,
        is_trainer: bool,
        now: float,
    ) -> tuple[BattleDetectorState, float, float]:
        """Returns (detector_state, grace_duration, since_last_seen)"""
        reading = vision.battle_reading_raw
        bt = vision.battle_text_raw
        ui_present = vision.hud_present
        ui_brightness = vision.ui_brightness

        if needs_reading and reading is not None and bt is not None:
            self._stable_in_battle, self._battle_debounce = debounce_battle(
                is_in_battle(reading.state, bt), self._battle_debounce
            )
            raw_in_battle = self._stable_in_battle
        else:
            is_active = (bt.menu_present or bt.action or bt.caught) if bt is not None else False
            self._stable_in_battle, self._battle_debounce = debounce_battle(
                is_active, self._battle_debounce
            )
            raw_in_battle = self._stable_in_battle

        # Translucency removal detection
        if raw_in_battle:
            if ui_present:
                self._was_ui_present = True
                self._battle_overlay_brightness = None
            elif self._was_ui_present:
                if self._battle_overlay_brightness is None:
                    self._battle_overlay_brightness = ui_brightness
                else:
                    baseline = self._battle_overlay_brightness
                    if baseline >= 15.0:
                        delta = 10.0 if baseline < 50.0 else 20.0
                        if ui_brightness > baseline + delta:
                            log.info(
                                f"overlay removed: {ui_brightness:.1f} > {baseline:.1f} + {delta}"
                            )
                            self._last_seen_battle = 0.0
                            raw_in_battle = False
                            self._stable_in_battle = False
                            self._battle_debounce = 0

        grace = battle_end_grace(
            is_trainer,
            ui_present,
            trainer_s=self.config.trainer_end_grace_s,
            anim_s=self.config.battle_anim_grace_s,
            normal_s=self.config.battle_end_grace_s,
        )

        if raw_in_battle:
            self._last_seen_battle = now
            return BattleDetectorState.ACTIVE, grace, 0.0

        if self._last_seen_battle > 0.0:
            since = now - self._last_seen_battle
            if since <= grace:
                return BattleDetectorState.GAP, grace, since
            else:
                self._last_seen_battle = 0.0

        return BattleDetectorState.IDLE, grace, 0.0
