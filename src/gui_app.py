"""Start BeatBridge's native PySide6 transition-building application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the BeatBridge native desktop app.")
    parser.add_argument("manifest", nargs="?", help="single-pair manifest.json (opens the optional review view)")
    parser.add_argument("--review-manifest", action="store_true", help="open the legacy batch-manifest review view")
    args = parser.parse_args()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 ist nicht installiert. Installiere die GUI-Abhängigkeiten mit "
            "'.venv\\Scripts\\python.exe -m pip install -r requirements-gui.txt'.",
            file=sys.stderr,
        )
        return 2

    app = QApplication(sys.argv[:1])
    app.setApplicationName("BeatBridge")
    app.setOrganizationName("BeatBridge")
    if args.review_manifest or args.manifest:
        from src.gui.main_window import BeatBridgeMainWindow

        window = BeatBridgeMainWindow()
        window.show()
    else:
        from src.gui.transition_builder import TransitionBuilderWindow

        window = TransitionBuilderWindow()
        window.show()
    if args.manifest:
        window.open_manifest(Path(args.manifest))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
