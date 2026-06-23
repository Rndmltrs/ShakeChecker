import os
import shutil

src = "src/overlay.py"
dst = "src/battle_panel.py"

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("class Overlay(QWidget):", "class BattlePanel(QWidget):")
content = content.replace("ov = Overlay(balls)", "ov = BattlePanel(balls)")
content = content.replace("CatchOverlay", "BattlePanel")

with open(dst, "w", encoding="utf-8") as f:
    f.write(content)
