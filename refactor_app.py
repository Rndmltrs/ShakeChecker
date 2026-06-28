import sys

with open(r"c:\Users\hailo\Desktop\ShakeChecker-Fork\src\core\app_controller.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
content = content.replace("from core.window_capture import (", "from ui.ui_manager import UIManager\nfrom core.window_capture import (")

# 2. Init body UI manager
old_init = """        self.battle_controller = battle_controller
        self.dex_controller = dex_controller
        self.mode_override: str = "auto" if self.settings.auto_switch else "dex"
        self.settings_controller = settings_controller

        self.battle_panel.set_hidden_names(self.settings_controller.hidden_ball_names())

        self.vision_controller = vision_controller

        if self.dex_panel is not None:
            self.dex_panel.on_mode_toggle = self._on_mode_toggle
            self.dex_panel.on_settings_click = lambda anchor: self.settings_controller.show(
                mode="dex", anchor_pos=anchor
            )

        self.battle_panel.on_settings_click = lambda anchor: self.settings_controller.show(
            mode="battle", anchor_pos=anchor
        )
        self.battle_panel.on_mode_toggle = self._on_mode_toggle"""

new_init = """        self.battle_controller = battle_controller
        self.dex_controller = dex_controller
        self.settings_controller = settings_controller
        self.ui_manager = UIManager(self.battle_panel, self.dex_panel, self.settings)

        self.battle_panel.set_hidden_names(self.settings_controller.hidden_ball_names())

        self.vision_controller = vision_controller

        if self.dex_panel is not None:
            self.dex_panel.on_mode_toggle = lambda: self.ui_manager.toggle_mode(self.state == AppState.BATTLE)
            self.dex_panel.on_settings_click = lambda anchor: self.settings_controller.show(
                mode="dex", anchor_pos=anchor
            )

        self.battle_panel.on_settings_click = lambda anchor: self.settings_controller.show(
            mode="battle", anchor_pos=anchor
        )
        self.battle_panel.on_mode_toggle = lambda: self.ui_manager.toggle_mode(self.state == AppState.BATTLE)"""
content = content.replace(old_init, new_init)

# 3. Unused vars
old_vars = """        self._last_hud = ""  # last resolved HUD location (drives dex panel refresh)
        self._loc_read = False  # location OCR'd this battle yet
        self._loc_ocr_raw = ""  # last raw OCR text (tracks what the screen actually shows)
        self._last_loc_mask: np.ndarray | None = None  # fast visual delta for location OCR
        self._loc_future: Future[str] | None = None  # background Location OCR task
        self._name_future: Future[dict[Any, Any] | None] | None = None  # background Name OCR task
        self._battle_loc_future: Future[Any] | None = None

        self._was_horde = False  # read_battle horde hint (read every tick, so init here)
        self._battle_debounce: int = 0  # frame counter for debounce_battle
        self._stable_in_battle: bool = False  # debounced battle membership
        self._last_loc_check = 0.0  # last IDLE location OCR (throttle)
        self._dex_log = ""  # last printed dex panel text (console dedup)"""

new_vars = """        self._last_hud = ""  # last resolved HUD location (drives dex panel refresh)
        self._loc_ocr_raw = ""  # last raw OCR text (tracks what the screen actually shows)
        self._battle_debounce: int = 0  # frame counter for debounce_battle
        self._stable_in_battle: bool = False  # debounced battle membership
        self._dex_log = ""  # last printed dex panel text (console dedup)"""
content = content.replace(old_vars, new_vars)

# 4. IPC Timer in start()
old_start = """        self.pool.submit(_load_ocr)
        log.info("waiting for PokeMMO window...")
        QTimer.singleShot(0, self.step)"""

new_start = """        self.pool.submit(_load_ocr)
        log.info("waiting for PokeMMO window...")
        
        # Inter-Process Communication (IPC): Watch for a quit signal file created by the
        # PowerShell launcher.
        self._quit_timer = QTimer()
        self._quit_timer.timeout.connect(self._check_quit)
        self._quit_timer.start(1000)
        
        QTimer.singleShot(0, self.step)

    def _check_quit(self) -> None:
        if os.path.exists(".shakechecker_quit"):
            with contextlib.suppress(OSError):
                os.remove(".shakechecker_quit")
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()"""
content = content.replace(old_start, new_start)

# 5. Remove _apply_mode_change, _on_mode_toggle
import re
content = re.sub(r"    def _apply_mode_change\(self, log_msg: str\) -> None:\n(?:        .*?\n)+?    def _handle_settings_update", "    def _handle_settings_update", content, flags=re.MULTILINE)


# 6. Simplify _handle_settings_update
old_handle_settings = """    def _handle_settings_update(self, update: SettingsUpdate) -> None:
        if update.settings_changed:
            self.settings.save()

        # Handle UI scale updates
        if update.scale_changed and self.hwnd is not None:
            client_rect = get_client_rect(self.hwnd)
            if client_rect is not None:
                if self.battle_panel.isVisible():
                    new_scale = self.settings.battle_scale or scale_for_window(client_rect.height)
                    self.battle_panel.apply_scale(new_scale)
                    self.battle_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)
                if self.dex_panel is not None and self.dex_panel.isVisible():
                    new_scale = self.settings.dex_scale or scale_for_window(client_rect.height)
                    self.dex_panel.apply_scale(new_scale)
                    self.dex_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)

        # Handle Ball toggles
        if update.settings_changed:
            self.battle_panel.set_hidden_names(self.settings_controller.hidden_ball_names())

        # Handle Mode overrides
        if update.toggle_auto_switch:
            if self.dex_panel is not None:
                self.dex_panel._hide_popups()
            if self.settings.auto_switch:
                self.mode_override = "auto"
            else:
                self.mode_override = "dex" if self.state == AppState.BATTLE else "battle"
            self._apply_mode_change(f"auto switch toggled, mode is now: {self.mode_override}")"""

new_handle_settings = """    def _handle_settings_update(self, update: SettingsUpdate) -> None:
        if update.settings_changed:
            self.settings.save()

        # Handle UI scale updates
        if update.scale_changed and self.hwnd is not None:
            client_rect = get_client_rect(self.hwnd)
            if client_rect is not None:
                self.ui_manager.sync_panel_positions()
                if self.battle_panel.isVisible():
                    self.battle_panel.apply_scale(
                        self.settings.battle_scale or scale_for_window(client_rect.height)
                    )
                    self.battle_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)
                if self.dex_panel is not None and self.dex_panel.isVisible():
                    self.dex_panel.apply_scale(
                        self.settings.dex_scale or scale_for_window(client_rect.height)
                    )
                    self.dex_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)

        # Handle Ball toggles
        if update.settings_changed:
            self.battle_panel.set_hidden_names(self.settings_controller.hidden_ball_names())

        # Handle Mode overrides
        if update.toggle_auto_switch:
            self.ui_manager.handle_auto_switch_toggled(self.state == AppState.BATTLE)
            if self.ui_manager.mode_override == "dex":
                self._refresh_dex_panel()"""
content = content.replace(old_handle_settings, new_handle_settings)

# Remove _set_owner
content = re.sub(r"    def _set_owner\(self, widget: QWidget \| None, owner_hwnd: int\) -> None:\n(?:        .*?\n)+?    def _tick", "    def _tick", content, flags=re.MULTILINE)

# Remove IPC check from _tick
old_tick_start = """    def _tick(self) -> float:

        # Inter-Process Communication (IPC): Watch for a quit signal file created by the
        # PowerShell launcher. This allows us to intercept the termination request and
        # shut down QApplication gracefully, ensuring our tray icon is cleaned up.
        # We throttle this check to once per second to avoid any unnecessary OS calls.
        if not hasattr(self, "_last_quit_check"):
            self._last_quit_check = 0.0

        current_time = time.monotonic()
        if current_time - self._last_quit_check > 1.0:
            self._last_quit_check = current_time
            if os.path.exists(".shakechecker_quit"):
                with contextlib.suppress(OSError):
                    os.remove(".shakechecker_quit")
                from PyQt6.QtWidgets import QApplication

                QApplication.quit()
                return 0.1

        if self.state is AppState.WAITING:"""
new_tick_start = """    def _tick(self) -> float:
        now = time.monotonic()
        
        if self.state is AppState.WAITING:"""
content = content.replace(old_tick_start, new_tick_start)

# Update state IDLE attachment
old_idle_attach = """            self.capture.hwnd = self.hwnd
            self._set_owner(self.battle_panel, self.hwnd)
            self._set_owner(self.dex_panel, self.hwnd)

            # Nudge panels above the game window once at startup
            from ui.ui_overlay import bring_overlay_above_game

            if self.battle_panel is not None:
                bring_overlay_above_game(self.battle_panel)
            if self.dex_panel is not None:
                bring_overlay_above_game(self.dex_panel)"""
new_idle_attach = """            self.capture.hwnd = self.hwnd
            self.ui_manager.attach_to_window(self.hwnd)"""
content = content.replace(old_idle_attach, new_idle_attach)

# Update window lost
old_win_lost = """            if not is_window_alive(self.hwnd):
                log.info("window lost, waiting...")
                if self.hwnd is not None:
                    self._set_owner(self.battle_panel, 0)
                    self._set_owner(self.dex_panel, 0)
                    self.hwnd = None
                if self.capture is not None:
                    self.capture.hwnd = 0
                self.state = AppState.WAITING
                self.battle_panel.hide_battle()
                if self.dex_panel is not None:
                    self.dex_panel.hide_panel()"""
new_win_lost = """            if not is_window_alive(self.hwnd):
                log.info("window lost, waiting...")
                if self.hwnd is not None:
                    self.ui_manager.detach_window()
                    self.hwnd = None
                if self.capture is not None:
                    self.capture.hwnd = 0
                self.state = AppState.WAITING"""
content = content.replace(old_win_lost, new_win_lost)


# Update battle needs_reading self.mode_override => self.ui_manager.mode_override
content = content.replace("self.mode_override != \"dex\"", "self.ui_manager.mode_override != \"dex\"")
content = content.replace("self.mode_override == \"auto\"", "self.ui_manager.mode_override == \"auto\"")

# now is defined earlier, remove "now = time.monotonic()"
content = content.replace("self._last_frame = frame\n        now = time.monotonic()\n", "self._last_frame = frame\n")

# Update auto mode in battle detected
old_battle_start = """            if self.state is not AppState.BATTLE:
                self.state = AppState.BATTLE
                if self.settings.auto_switch:
                    self.mode_override = "auto"
                log.info("battle detected")
                self.battle_controller.reset(now)
                if self.dex_panel is not None:
                    self.dex_panel.hide_panel()"""
new_battle_start = """            if self.state is not AppState.BATTLE:
                self.state = AppState.BATTLE
                self.ui_manager.on_battle_start()
                log.info("battle detected")
                self.battle_controller.reset(now)"""
content = content.replace(old_battle_start, new_battle_start)

# Update battle panel update
old_battle_update = """            if self.mode_override != "dex":
                self.battle_panel.set_loading(update.is_loading)
                if update.panel_state is not None:
                    self.battle_panel.apply_scale(
                        self.settings.battle_scale or scale_for_window(client_rect.height)
                    )
                    self.battle_panel.show_battle(**update.panel_state)
                    self.battle_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)"""
new_battle_update = """            self.ui_manager.update_battle_panel(update.panel_state, client_rect, update.is_loading)"""
# wait, there's `if self.mode_override != "dex":` which I replaced to `self.ui_manager.mode_override` earlier
old_battle_update_fixed = """            if self.ui_manager.mode_override != "dex":
                self.battle_panel.set_loading(update.is_loading)
                if update.panel_state is not None:
                    self.battle_panel.apply_scale(
                        self.settings.battle_scale or scale_for_window(client_rect.height)
                    )
                    self.battle_panel.show_battle(**update.panel_state)
                    self.battle_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)"""
content = content.replace(old_battle_update_fixed, new_battle_update)

# Update battle end
old_battle_end = """        elif self.state is AppState.BATTLE and now - self.last_seen_battle > grace:
            self.state = AppState.IDLE
            if self.settings.auto_switch:
                self.mode_override = "auto"
            self.last_line = ""
            if (
                not self.battle_controller._caught_printed
            ):  # after a catch we already said "caught X!"
                log.info("battle ended")
            self._battle_debounce = 0
            self._stable_in_battle = False
            self.vision_controller.reset()
            self.battle_panel.hide_battle()"""
new_battle_end = """        elif self.state is AppState.BATTLE and now - self.last_seen_battle > grace:
            self.state = AppState.IDLE
            self.ui_manager.on_battle_end()
            self.last_line = ""
            if (
                not self.battle_controller._caught_printed
            ):  # after a catch we already said "caught X!"
                log.info("battle ended")
            self._battle_debounce = 0
            self._stable_in_battle = False
            self.vision_controller.reset()"""
content = content.replace(old_battle_end, new_battle_end)

# Update dex panel update
old_dex_update = """            if (
                (
                    self.ui_manager.mode_override == "dex"
                    or (
                        self.ui_manager.mode_override == "auto"
                        and self.settings.auto_switch
                        and self.state != AppState.BATTLE
                    )
                )
                and self.dex_panel is not None
                and dex_update.location_view is not None
            ):
                self.dex_panel.apply_scale(
                    self.settings.dex_scale or scale_for_window(client_rect.height)
                )
                if self.ui_manager.mode_override != "battle":
                    self.dex_panel.show_here(dex_update.location_view)
                self.dex_panel.dock_to(client_rect.left, client_rect.top, client_rect.width)

        # Apply manual mode override UI forcing
        if self.ui_manager.mode_override == "dex":
            if self.battle_panel.isVisible():
                self.battle_panel.hide()
            if (
                self.state == AppState.BATTLE
                and self.dex_panel is not None
                and not self.dex_panel.isVisible()
            ):
                self.dex_panel.show()
        elif self.ui_manager.mode_override == "battle":
            if self.dex_panel is not None and self.dex_panel.isVisible():
                self.dex_panel.hide_panel()
            if self.state == AppState.IDLE and not self.battle_panel.isVisible():
                self.battle_panel.apply_scale(
                    self.settings.battle_scale or scale_for_window(client_rect.height)
                )
                self.battle_panel.show_battle(
                    dex_id=0,
                    name="—",
                    catch_rate=None,
                    turn=0,
                    probs={},
                    is_empty=True,
                )
        # Sync positions so toggling doesn't cause panels to jump
        bp_pos = getattr(self.battle_panel, "_last_pos", None)
        dp_pos = getattr(self.dex_panel, "_last_pos", None) if self.dex_panel is not None else None

        if self.battle_panel.isVisible() and bp_pos is not None:
            if self.dex_panel is not None:
                self.dex_panel._last_pos = bp_pos
                self.dex_panel.move(*bp_pos)
        elif (
            self.dex_panel is not None
            and self.dex_panel.isVisible()
            and dp_pos is not None
            or self.battle_panel.isVisible()
            and bp_pos is None
            and dp_pos is not None
        ):
            self.battle_panel._last_pos = dp_pos
            self.battle_panel.move(*dp_pos)
        elif (
            self.dex_panel is not None
            and self.dex_panel.isVisible()
            and dp_pos is None
            and bp_pos is not None
        ):
            self.dex_panel._last_pos = bp_pos
            self.dex_panel.move(*bp_pos)"""

new_dex_update = """            self.ui_manager.update_dex_panel(dex_update.location_view, client_rect, dex_update.is_loading, in_battle)

        self.ui_manager.enforce_mode_ui(self.state == AppState.BATTLE, client_rect)"""
content = content.replace(old_dex_update, new_dex_update)

# force refresh loc
content = content.replace("""    def _force_refresh_loc(self) -> None:
        if hasattr(self, "dex_controller"):
            self.dex_controller.force_refresh()
        self._last_hud = ""
        self._last_loc_mask = None
        log.info("Forced location refresh via Dex panel")""", """    def _force_refresh_loc(self) -> None:
        if hasattr(self, "dex_controller"):
            self.dex_controller.force_refresh()
        self._last_hud = ""
        log.info("Forced location refresh via Dex panel")""")

# force refresh battle
content = content.replace("""    def _force_refresh_battle(self) -> None:
        self._was_horde = False
        self._loc_read = False
        if hasattr(self, "battle_controller"):
            self.battle_controller.force_refresh()
        log.info("Forced battle state refresh via Battle panel")""", """    def _force_refresh_battle(self) -> None:
        if hasattr(self, "battle_controller"):
            self.battle_controller.force_refresh()
        log.info("Forced battle state refresh via Battle panel")""")


with open(r"c:\Users\hailo\Desktop\ShakeChecker-Fork\src\core\app_controller.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
