# src/main.py
import sys
from PySide6.QtWidgets import QApplication
from src.db_sqlite import init_sqlite_db
from src.ui import SchedulerMainWindow

def main():
    # Setup state database tables
    init_sqlite_db()
    
    # Initialize UI elements
    app = QApplication(sys.argv)
    window = SchedulerMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
