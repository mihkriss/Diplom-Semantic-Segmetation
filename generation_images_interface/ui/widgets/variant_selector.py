import io
from typing import List
from PIL import Image
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage

from .clickable_label import ClickableLabel

class VariantSelector(QWidget):
    """Виджет для выбора варианта изображения"""
    
    variant_selected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_index = -1
        self.pixmaps: List[QPixmap] = []
        self.labels: List[ClickableLabel] = []
        self.init_ui()
        
    def init_ui(self):
        """Инициализировать интерфейс"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.title = QLabel("📸 Выберите лучший вариант:")
        self.title.setStyleSheet("font-size: 16px; font-weight: bold; color: #9C27B0;")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        
        self.variants_layout = QHBoxLayout()
        self.variants_layout.setSpacing(15)
        self.variants_layout.setAlignment(Qt.AlignCenter)
        
        layout.addLayout(self.variants_layout)
        self.setLayout(layout)
        
    def set_variants(self, images: List[Image.Image]):
        """Установить варианты изображений"""
        self._clear_previous()
        
        for i, img in enumerate(images):
            pixmap = self._pil_to_qpixmap(img)
            self.pixmaps.append(pixmap)
            
            label = self._create_variant_label(pixmap, i)
            self.variants_layout.addWidget(label)
            self.labels.append(label)
        
        self.title.setText(f"📸 Выберите лучший вариант (1-{len(images)}):")
    
    def _clear_previous(self):
        """Очистить предыдущие варианты"""
        while self.variants_layout.count():
            item = self.variants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.pixmaps.clear()
        self.labels.clear()
        self.selected_index = -1
    
    def _pil_to_qpixmap(self, pil_image: Image.Image) -> QPixmap:
        """Конвертировать PIL в QPixmap"""
        byte_array = io.BytesIO()
        pil_image.save(byte_array, format='PNG')
        byte_array.seek(0)
        
        qimage = QImage()
        qimage.loadFromData(byte_array.getvalue())
        return QPixmap.fromImage(qimage)
    
    def _create_variant_label(self, pixmap: QPixmap, index: int) -> ClickableLabel:
        """Создать метку для варианта"""
        label = ClickableLabel()
        label.set_variant_index(index)
        label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(self._get_label_style(selected=False))
        label.clicked.connect(lambda idx=index: self.select_variant(idx))
        return label
    
    def _get_label_style(self, selected: bool = False) -> str:
        """Получить стиль для метки"""
        if selected:
            return """
                QLabel {
                    border: 3px solid #4CAF50;
                    border-radius: 5px;
                    background-color: #e8f5e9;
                }
            """
        else:
            return """
                QLabel {
                    border: 3px solid #ccc;
                    border-radius: 5px;
                    background-color: #fafafa;
                }
                QLabel:hover {
                    border: 3px solid #2196F3;
                }
            """
    
    def select_variant(self, index: int):
        """Выбрать вариант"""
        self.selected_index = index
        
        for i, label in enumerate(self.labels):
            label.setStyleSheet(self._get_label_style(selected=(i == index)))
        
        self.variant_selected.emit(index)