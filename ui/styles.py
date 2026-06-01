class Styles:
    """Стили для интерфейса"""
    
    @staticmethod
    def get_button_style(button_type: str) -> str:
        """Получить стиль для кнопки"""
        styles = {
            "primary": """
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                }
                QPushButton:checked {
                    background-color: #9C27B0;
                    font-weight: bold;
                }
            """,
            "success": """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 15px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:disabled { 
                    background-color: #cccccc; 
                }
            """,
            "warning": """
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                }
            """,
            "info": """
                QPushButton {
                    background-color: #00BCD4;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                }
            """
        }
        return styles.get(button_type, "")
    
    @staticmethod
    def get_progress_bar_style() -> str:
        """Получить стиль для прогресс-бара"""
        return """
            QProgressBar {
                border: 2px solid #9C27B0;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #9C27B0;
                border-radius: 3px;
            }
        """
    
    @staticmethod
    def get_image_label_style(border_color: str = "#9C27B0") -> str:
        """Получить стиль для метки изображения"""
        return f"""
            QLabel {{
                border: 3px solid {border_color};
                border-radius: 5px;
                background-color: #fafafa;
            }}
        """