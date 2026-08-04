import sys
from PyQt6.QtWidgets import QApplication
from src.config import AppConfig
from src.ui.main_window import MainWindow

app = QApplication(sys.argv)
config = AppConfig()
win = MainWindow(config)
print("MainWindow instantiated successfully.")
