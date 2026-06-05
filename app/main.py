from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# On some Windows/Python builds, loading Qt before PyTorch can make torch DLL
# initialization fail. Preload the ML stack before QApplication is created.
try:
    import torch  # noqa: F401
    import ultralytics  # noqa: F401
except Exception:
    pass

from PyQt5.QtWidgets import QApplication, QMessageBox

from app.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, "Startup error", str(exc))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
