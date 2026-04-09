"""MatTrack — Material Lifecycle Tracker entry point."""

import sys

from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from db.connection import get_connection
from db.schema import initialize_schema
from ui.main_window import MainWindow


def main() -> None:
    conn = get_connection()
    initialize_schema(conn)

    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="light_blue.xml")

    window = MainWindow(conn)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
