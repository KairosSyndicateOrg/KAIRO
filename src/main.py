import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from bridge import KairoBridge


def main():
    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()

    bridge = KairoBridge()

    engine.rootContext().setContextProperty(
        "kairoBridge",
        bridge
    )

    qml_file = Path(__file__).parent / "gui" / "gui.qml"

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()