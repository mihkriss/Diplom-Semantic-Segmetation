from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import pyqtSignal

class ClickableLabel(QLabel):
    """Кликабельная метка для выбора варианта"""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.variant_index = -1
        
    def set_variant_index(self, index: int):
        """Установить индекс варианта"""
        self.variant_index = index
        
    def mousePressEvent(self, event):
        """Обработка клика"""
        self.clicked.emit()
        super().mousePressEvent(event)