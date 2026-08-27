# src/main.py
import sys
from PySide6.QtWidgets import QApplication
from src.db_sqlite import init_sqlite_db
from src.ui import SchedulerMainWindow
from src.ui import APP_STYLING
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

def main():
    # Setup state database tables
    init_sqlite_db()
    
    # Initialize UI elements
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLING)
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor("#FFFFFF"))
    palette.setColor(QPalette.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.WindowText, QColor("#1F2937"))
    palette.setColor(QPalette.Text, QColor("#1F2937"))
    app.setPalette(palette)
    window = SchedulerMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
