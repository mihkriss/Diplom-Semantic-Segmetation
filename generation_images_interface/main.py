import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from config import Config

print("=" * 70)
print("🏙️ LoRA DATASET - БОЛЬШИЕ ИЗОБРАЖЕНИЯ")
print("=" * 70)

def main():
    """Точка входа в приложение"""
    Config.ensure_output_dir()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow(Config)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()