
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui.main_window import SimulatorMainWindow

if __name__ == "__main__":

  
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    
    window = SimulatorMainWindow()
    window.show()
    
    sys.exit(app.exec())