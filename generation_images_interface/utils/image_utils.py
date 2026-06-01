import io
from PIL import Image
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

def pil_to_pixmap(pil_image: Image.Image) -> QPixmap:
    """Конвертировать PIL изображение в QPixmap"""
    try:
        byte_array = io.BytesIO()
        pil_image.save(byte_array, format='PNG')
        byte_array.seek(0)
        
        qimage = QImage()
        if qimage.loadFromData(byte_array.getvalue()):
            return QPixmap.fromImage(qimage)
        return QPixmap()
    except Exception as e:
        print(f"Ошибка конвертации изображения: {e}")
        return QPixmap()

def scale_pixmap(pixmap: QPixmap, width: int, height: int) -> QPixmap:
    """Масштабировать QPixmap с сохранением пропорций"""
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

def get_image_size_info(width: int, height: int) -> tuple:
    """Получить информацию о размере изображения и рекомендации по памяти"""
    pixels = width * height
    
    if pixels > 1024 * 1024:
        return "⚠️ Размер >1MP требует много памяти GPU", "#f44336"
    elif pixels > 768 * 768:
        return "⚠️ Размер >768x768 требует больше памяти GPU", "#FF9800"
    else:
        return "✅ Размер оптимален для 8GB GPU", "#4CAF50"