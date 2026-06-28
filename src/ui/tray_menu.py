from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


def build_tray(icon: QIcon, on_quit, version: str) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(icon)
    tray.setToolTip(f"ShakeChecker v{version}")
    menu = QMenu()
    quit_action = QAction("Quit ShakeChecker", menu)
    quit_action.triggered.connect(on_quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.show()
    tray.showMessage(
        "ShakeChecker",
        f"v{version} is running. Right-click the tray icon to quit.",
        QSystemTrayIcon.MessageIcon.Information,
        4000,
    )
    return tray
