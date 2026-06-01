import os
import sys
import json
from datetime import datetime
from typing import Optional, List

from PIL import Image
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QTextEdit, QSlider, QSpinBox,
    QProgressBar, QListWidget, QScrollArea, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from config import Config
from core.dataset_manager import DatasetManager
from core.image_generator import ImageGenerator
from ui.widgets.variant_selector import VariantSelector
from ui.styles import Styles
from utils.image_utils import pil_to_pixmap, scale_pixmap, get_image_size_info


class MainWindow(QMainWindow):
    """Главное окно приложения для генерации изображений с LoRA"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        # Состояние приложения
        self.current_image: Optional[Image.Image] = None
        self.source_image: Optional[Image.Image] = None
        self.generated_images: List[Image.Image] = []
        self.selected_variant_index: int = -1
        self.dataset_manager: Optional[DatasetManager] = None
        self.generation_mode: str = "img2img"
        self.current_zoom: float = 1.0
        self.source_pixmap: Optional[QPixmap] = None
        self.worker: Optional[ImageGenerator] = None
        
        # Инициализация UI
        self.init_ui()
        self.load_dataset()
        self.check_lora()
        
    # ========== ИНИЦИАЛИЗАЦИЯ UI ==========
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("🏙️ LoRA Dataset - Мультивариантная генерация")
        self.setGeometry(100, 100, 2000, 1100)
        
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)
        
        # Левая панель (управление)
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Правая панель (изображения)
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel)
    
    def _create_left_panel(self) -> QWidget:
        """Создать левую панель управления"""
        left = QWidget()
        left.setMaximumWidth(520)
        left_layout = QVBoxLayout()
        left.setLayout(left_layout)
        
        # Заголовок
        title = QLabel("🏙️ LoRA Generator")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #9C27B0; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)
        
        # Компоненты панели
        left_layout.addWidget(self._create_mode_group())
        left_layout.addWidget(self._create_info_group())
        left_layout.addWidget(self._create_dataset_group())
        left_layout.addWidget(self._create_prompt_group())
        left_layout.addWidget(self._create_variants_group())
        left_layout.addWidget(self._create_size_group())
        left_layout.addWidget(self._create_params_group())
        left_layout.addWidget(self._create_action_buttons())
        left_layout.addWidget(self._create_status_label())
        left_layout.addStretch()
        
        return left
    
    def _create_right_panel(self) -> QWidget:
        """Создать правую панель с изображениями"""
        right = QWidget()
        right_layout = QVBoxLayout()
        right.setLayout(right_layout)
        
        # Прогресс
        right_layout.addWidget(self._create_progress_group())
        
        # Заголовок сравнения
        self.comparison_title = QLabel("🔄 Сравнение: исходное → сгенерированное")
        self.comparison_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-top: 10px;")
        self.comparison_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.comparison_title)
        
        # Область с прокруткой
        scroll_area = self._create_scrollable_images_area()
        right_layout.addWidget(scroll_area)
        
        # Кнопки управления
        right_layout.addLayout(self._create_image_control_buttons())
        
        return right
    
    # ========== СОЗДАНИЕ ГРУПП UI ==========
    
    def _create_mode_group(self) -> QGroupBox:
        """Создать группу выбора режима генерации"""
        group = QGroupBox("🎯 Режим генерации")
        layout = QVBoxLayout()
        
        # Кнопки режимов
        buttons_layout = QHBoxLayout()
        
        self.img2img_btn = QPushButton("🖼️ Img2Img (с изображением)")
        self.txt2img_btn = QPushButton("📝 Txt2Img (только текст)")
        
        for btn in [self.img2img_btn, self.txt2img_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet(Styles.get_button_style("primary"))
        
        self.img2img_btn.setChecked(True)
        self.img2img_btn.clicked.connect(lambda: self.set_mode("img2img"))
        self.txt2img_btn.clicked.connect(lambda: self.set_mode("txt2img"))
        
        buttons_layout.addWidget(self.img2img_btn)
        buttons_layout.addWidget(self.txt2img_btn)
        layout.addLayout(buttons_layout)
        
        # Информация о режиме
        self.mode_info_label = QLabel("ℹ️ Img2Img: использует изображение из датасета как основу")
        self.mode_info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        self.mode_info_label.setWordWrap(True)
        layout.addWidget(self.mode_info_label)
        
        group.setLayout(layout)
        return group
    
    def _create_info_group(self) -> QGroupBox:
        """Создать группу информации"""
        group = QGroupBox("ℹ️ Информация")
        layout = QVBoxLayout()
        
        self.lora_status = QLabel("⏳ Проверка LoRA...")
        self.token_label = QLabel("🏷️ Токен: sks")
        self.token_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        self.dataset_info = QLabel("📊 Датасет: загрузка...")
        
        for label in [self.lora_status, self.token_label, self.dataset_info]:
            layout.addWidget(label)
        
        group.setLayout(layout)
        return group
    
    def _create_dataset_group(self) -> QGroupBox:
        """Создать группу выбора изображения из датасета"""
        self.dataset_group = QGroupBox("📁 Выбор изображения из датасета")
        layout = QVBoxLayout()
        
        # Кнопка загрузки
        self.load_dataset_btn = QPushButton("🔄 Загрузить датасет")
        self.load_dataset_btn.clicked.connect(self.load_dataset)
        self.load_dataset_btn.setStyleSheet(Styles.get_button_style("primary"))
        layout.addWidget(self.load_dataset_btn)
        
        # Список датасета
        self.dataset_list = QListWidget()
        self.dataset_list.setMaximumHeight(200)
        self.dataset_list.itemClicked.connect(self.on_dataset_selected)
        layout.addWidget(self.dataset_list)
        
        # Оригинальный промпт
        self.original_prompt_label = QLabel("📝 Оригинальный промпт:")
        layout.addWidget(self.original_prompt_label)
        
        self.original_prompt_text = QTextEdit()
        self.original_prompt_text.setMaximumHeight(50)
        self.original_prompt_text.setReadOnly(True)
        self.original_prompt_text.setStyleSheet("background-color: #f0f0f0;")
        layout.addWidget(self.original_prompt_text)
        
        self.dataset_group.setLayout(layout)
        return self.dataset_group
    
    def _create_prompt_group(self) -> QGroupBox:
        """Создать группу ввода промпта"""
        group = QGroupBox("📝 Ваш промпт")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Используйте 'sks' для вашего стиля:"))
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlainText("a sks panel building with a red car parked in front")
        self.prompt_text.setMaximumHeight(60)
        layout.addWidget(self.prompt_text)
        
        # Быстрые кнопки
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Быстрое добавление:"))
        
        quick_words = ["car", "trees", "factory", "road", "panel build"]
        for word in quick_words:
            btn = QPushButton(f"+{word}")
            btn.clicked.connect(lambda checked, w=word: self.add_to_prompt(w))
            btn.setMaximumWidth(70)
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        group.setLayout(layout)
        return group
    
    def _create_variants_group(self) -> QGroupBox:
        """Создать группу выбора количества вариантов"""
        group = QGroupBox("🔢 Количество вариантов")
        layout = QVBoxLayout()
        
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Вариантов:"))
        
        self.variants_slider = QSlider(Qt.Horizontal)
        self.variants_slider.setRange(1, 9)
        self.variants_slider.setValue(4)
        
        self.variants_label = QLabel("4")
        self.variants_slider.valueChanged.connect(lambda v: self.variants_label.setText(str(v)))
        
        slider_layout.addWidget(self.variants_slider)
        slider_layout.addWidget(self.variants_label)
        layout.addLayout(slider_layout)
        
        info_label = QLabel("ℹ️ Больше вариантов = больше времени генерации")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label)
        
        group.setLayout(layout)
        return group
    
    def _create_size_group(self) -> QGroupBox:
        """Создать группу выбора размера изображения"""
        group = QGroupBox("📐 Выбор размера изображения")
        layout = QVBoxLayout()
        
        # Пресеты размеров
        layout.addWidget(QLabel("Быстрый выбор размера:"))
        presets_layout = QHBoxLayout()
        
        size_presets = [
            ("512x512", 512, 512),
            ("640x640", 640, 640),
            ("768x768", 768, 768),
            ("1024x576", 1024, 576),
            ("576x1024", 576, 1024),
            ("1280x720", 1280, 720),
            ("1920x1080", 1920, 1080),
        ]
        
        for name, w, h in size_presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, width=w, height=h: self.set_size_preset(width, height))
            btn.setMaximumWidth(80)
            presets_layout.addWidget(btn)
        
        layout.addLayout(presets_layout)
        
        # Ручной ввод
        layout.addWidget(QLabel("Или введите вручную:"))
        manual_layout = QGridLayout()
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(256, 2048)
        self.width_spin.setValue(768)
        self.width_spin.setSingleStep(64)
        self.width_spin.valueChanged.connect(self.update_size_label)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(256, 2048)
        self.height_spin.setValue(768)
        self.height_spin.setSingleStep(64)
        self.height_spin.valueChanged.connect(self.update_size_label)
        
        manual_layout.addWidget(QLabel("Ширина:"), 0, 0)
        manual_layout.addWidget(self.width_spin, 0, 1)
        manual_layout.addWidget(QLabel("Высота:"), 1, 0)
        manual_layout.addWidget(self.height_spin, 1, 1)
        layout.addLayout(manual_layout)
        
        # Информация о размере
        self.size_info_label = QLabel("Текущий размер: 768x768")
        self.size_info_label.setAlignment(Qt.AlignCenter)
        self.size_info_label.setStyleSheet("color: #9C27B0; font-weight: bold; padding: 5px;")
        layout.addWidget(self.size_info_label)
        
        self.memory_warning = QLabel("⚠️ Размер >768px требует больше памяти GPU")
        self.memory_warning.setStyleSheet("color: #FF9800; font-size: 11px;")
        self.memory_warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.memory_warning)
        
        group.setLayout(layout)
        return group
    
    def _create_params_group(self) -> QGroupBox:
        """Создать группу параметров генерации"""
        group = QGroupBox("⚙️ Параметры")
        layout = QVBoxLayout()
        
        # Strength (сила влияния)
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Сила влияния:"))
        
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(30, 90)
        self.strength_slider.setValue(65)
        
        self.strength_label = QLabel("0.65")
        self.strength_slider.valueChanged.connect(
            lambda v: self.strength_label.setText(f"{v/100:.2f}")
        )
        
        strength_layout.addWidget(self.strength_slider)
        strength_layout.addWidget(self.strength_label)
        layout.addLayout(strength_layout)
        
        # Steps (шаги)
        steps_layout = QHBoxLayout()
        steps_layout.addWidget(QLabel("Шаги:"))
        
        self.steps_slider = QSlider(Qt.Horizontal)
        self.steps_slider.setRange(20, 70)
        self.steps_slider.setValue(30)
        
        self.steps_label = QLabel("30")
        self.steps_slider.valueChanged.connect(lambda v: self.steps_label.setText(str(v)))
        
        steps_layout.addWidget(self.steps_slider)
        steps_layout.addWidget(self.steps_label)
        layout.addLayout(steps_layout)
        
        # Guidance
        guidance_layout = QHBoxLayout()
        guidance_layout.addWidget(QLabel("Guidance:"))
        
        self.guidance_slider = QSlider(Qt.Horizontal)
        self.guidance_slider.setRange(1, 15)
        self.guidance_slider.setValue(7)
        
        self.guidance_label = QLabel("7.0")
        self.guidance_slider.valueChanged.connect(
            lambda v: self.guidance_label.setText(f"{v/2:.1f}")
        )
        
        guidance_layout.addWidget(self.guidance_slider)
        guidance_layout.addWidget(self.guidance_label)
        layout.addLayout(guidance_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_action_buttons(self) -> QWidget:
        """Создать кнопки действий"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        self.generate_btn = QPushButton("🎨 СГЕНЕРИРОВАТЬ")
        self.generate_btn.setStyleSheet(Styles.get_button_style("success"))
        self.generate_btn.clicked.connect(self.generate)
        self.generate_btn.setEnabled(False)
        layout.addWidget(self.generate_btn)
        
        self.save_btn = QPushButton("💾 Сохранить выбранный")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setStyleSheet(Styles.get_button_style("warning"))
        layout.addWidget(self.save_btn)
        
        self.save_all_btn = QPushButton("💾 Сохранить все варианты")
        self.save_all_btn.setEnabled(False)
        self.save_all_btn.clicked.connect(self.save_all)
        self.save_all_btn.setStyleSheet(Styles.get_button_style("info"))
        layout.addWidget(self.save_all_btn)
        
        return widget
    
    def _create_status_label(self) -> QLabel:
        """Создать метку статуса"""
        self.status_label = QLabel("✅ Загрузите датасет")
        self.status_label.setStyleSheet("padding: 10px; background: #f5f5f5; border-radius: 5px;")
        return self.status_label
    
    def _create_progress_group(self) -> QGroupBox:
        """Создать группу прогресса"""
        group = QGroupBox("📊 Прогресс генерации")
        layout = QVBoxLayout()
        
        self.progress_status = QLabel("⚪ Ожидание генерации")
        self.progress_status.setAlignment(Qt.AlignCenter)
        self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #666;")
        layout.addWidget(self.progress_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(Styles.get_progress_bar_style())
        layout.addWidget(self.progress_bar)
        
        self.progress_details = QLabel("Шаг 0/0 • 0%")
        self.progress_details.setAlignment(Qt.AlignCenter)
        self.progress_details.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.progress_details)
        
        group.setLayout(layout)
        return group
    
    def _create_scrollable_images_area(self) -> QScrollArea:
        """Создать прокручиваемую область для изображений"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        container = QWidget()
        layout = QVBoxLayout()
        container.setLayout(layout)
        
        # Исходное изображение
        source_box = QGroupBox("Исходное изображение из датасета")
        source_layout = QVBoxLayout()
        
        self.source_image_label = QLabel()
        self.source_image_label.setAlignment(Qt.AlignCenter)
        self.source_image_label.setStyleSheet(Styles.get_image_label_style("#9C27B0"))
        self.source_image_label.setText("Выберите\nизображение\nиз датасета")
        self.source_image_label.setMinimumSize(300, 300)
        
        source_layout.addWidget(self.source_image_label)
        source_box.setLayout(source_layout)
        layout.addWidget(source_box)
        
        # Селектор вариантов
        self.variant_selector = VariantSelector()
        self.variant_selector.variant_selected.connect(self.on_variant_selected)
        self.variant_selector.setVisible(False)
        layout.addWidget(self.variant_selector)
        
        # Выбранное изображение
        self.selected_view_box = QGroupBox("👁️ Выбранный вариант (для сохранения)")
        selected_view_layout = QVBoxLayout()
        
        self.selected_image_label = QLabel()
        self.selected_image_label.setAlignment(Qt.AlignCenter)
        self.selected_image_label.setStyleSheet(Styles.get_image_label_style("#4CAF50"))
        self.selected_image_label.setText("Выберите\nвариант\nвыше")
        self.selected_image_label.setMinimumSize(400, 400)
        
        selected_view_layout.addWidget(self.selected_image_label)
        self.selected_view_box.setLayout(selected_view_layout)
        self.selected_view_box.setVisible(False)
        layout.addWidget(self.selected_view_box)
        
        scroll_area.setWidget(container)
        return scroll_area
    
    def _create_image_control_buttons(self) -> QHBoxLayout:
        """Создать кнопки управления изображениями"""
        layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("🗑️ Очистить")
        self.clear_btn.clicked.connect(self.clear_all)
        self.clear_btn.setStyleSheet("padding: 8px;")
        layout.addWidget(self.clear_btn)
        
        self.open_folder_btn = QPushButton("📂 Открыть папку с результатами")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setStyleSheet("padding: 8px;")
        layout.addWidget(self.open_folder_btn)
        
        layout.addStretch()
        
        # Кнопки зума
        self.zoom_out_btn = QPushButton("🔍 -")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_out_btn.setMaximumWidth(50)
        layout.addWidget(self.zoom_out_btn)
        
        self.zoom_reset_btn = QPushButton("🔄 100%")
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        self.zoom_reset_btn.setMaximumWidth(70)
        layout.addWidget(self.zoom_reset_btn)
        
        self.zoom_in_btn = QPushButton("🔍 +")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_in_btn.setMaximumWidth(50)
        layout.addWidget(self.zoom_in_btn)
        
        return layout
    
    # ========== МЕТОДЫ УПРАВЛЕНИЯ ==========
    
    def set_mode(self, mode: str):
        """Переключение режима генерации"""
        self.generation_mode = mode
        
        if mode == "img2img":
            self.img2img_btn.setChecked(True)
            self.txt2img_btn.setChecked(False)
            self.mode_info_label.setText("ℹ️ Img2Img: использует изображение из датасета как основу")
            self.dataset_group.setEnabled(True)
            self.strength_slider.setEnabled(True)
            self.strength_label.setEnabled(True)
            self.source_image_label.setEnabled(True)
            self.comparison_title.setText("🔄 Сравнение: исходное → сгенерированное")
            self.generate_btn.setEnabled(self.source_image is not None)
        else:
            self.img2img_btn.setChecked(False)
            self.txt2img_btn.setChecked(True)
            self.mode_info_label.setText("ℹ️ Txt2Img: генерация с нуля только по текстовому промпту")
            self.dataset_group.setEnabled(False)
            self.strength_slider.setEnabled(False)
            self.strength_label.setEnabled(False)
            self.source_image_label.setEnabled(False)
            self.comparison_title.setText("📝 Генерация с нуля по тексту")
            self.generate_btn.setEnabled(True)
        
        self.update_size_label()
    
    def set_size_preset(self, width: int, height: int):
        """Установить пресет размера"""
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
    
    def update_size_label(self):
        """Обновить метку размера"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        self.size_info_label.setText(f"Текущий размер: {width}x{height}")
        
        if self.generation_mode == "img2img":
            self.comparison_title.setText(f"🔄 Сравнение: исходное → сгенерированное ({width}x{height})")
        else:
            self.comparison_title.setText(f"📝 Генерация с нуля по тексту ({width}x{height})")
        
        # Обновление предупреждения о памяти
        warning_text, color = get_image_size_info(width, height)
        self.memory_warning.setText(warning_text)
        self.memory_warning.setStyleSheet(f"color: {color}; font-size: 11px;")
    
    def add_to_prompt(self, text: str):
        """Добавить текст к промпту"""
        current = self.prompt_text.toPlainText()
        if current.strip():
            new_text = f"{current}, {text}"
        else:
            new_text = f"sks {text}"
        self.prompt_text.setPlainText(new_text)
    
    # ========== РАБОТА С ДАТАСЕТОМ ==========
    
    def load_dataset(self):
        """Загрузить датасет"""
        try:
            self.dataset_manager = DatasetManager(
                self.config.metadata_file,
                self.config.dataset_path
            )
            
            if not self.dataset_manager.is_empty():
                self.dataset_list.clear()
                
                for i, sample in enumerate(self.dataset_manager.samples):
                    filename = sample['file_name']
                    prompt = sample.get('text', '')
                    short_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
                    item_text = f"{i+1}. {filename}\n   {short_prompt}"
                    self.dataset_list.addItem(item_text)
                
                self.dataset_info.setText(f"📊 Датасет: {len(self.dataset_manager)} изображений")
                self.status_label.setText(f"✅ Загружено {len(self.dataset_manager)} изображений")
            else:
                QMessageBox.warning(self, "Предупреждение", "Датасет пуст или не найден")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить датасет:\n{e}")
    
    def on_dataset_selected(self, item):
        """Обработка выбора элемента датасета"""
        try:
            index = self.dataset_list.row(item)
            
            image_path = self.dataset_manager.get_image_path(index)
            prompt = self.dataset_manager.get_prompt(index)
            
            if image_path and os.path.exists(image_path):
                self.source_image = Image.open(image_path).convert('RGB')
                self.display_source_image(self.source_image)
                self.original_prompt_text.setPlainText(prompt)
                self.prompt_text.setPlainText(prompt.lower())
                
                if self.generation_mode == "img2img":
                    self.generate_btn.setEnabled(True)
                
                self.status_label.setText(f"✅ Выбрано: {os.path.basename(image_path)}")
            else:
                QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{image_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки изображения:\n{e}")
    
    def display_source_image(self, pil_image: Image.Image):
        """Отобразить исходное изображение"""
        self.source_pixmap = pil_to_pixmap(pil_image)
        if not self.source_pixmap.isNull():
            zoomed = scale_pixmap(self.source_pixmap, 300, 300)
            self.source_image_label.setPixmap(zoomed)
            self.source_image_label.setText("")
    
    def check_lora(self):
        """Проверить наличие LoRA модели"""
        if os.path.exists(self.config.lora_path):
            self.lora_status.setText("✅ LoRA модель найдена")
            self.lora_status.setStyleSheet("color: #4CAF50;")
        else:
            self.lora_status.setText("❌ LoRA модель не найдена")
            self.lora_status.setStyleSheet("color: #f44336;")
    
    # ========== ГЕНЕРАЦИЯ ==========
    
    def generate(self):
        """Запустить генерацию"""
        if self.generation_mode == "img2img" and not self.source_image:
            QMessageBox.warning(self, "Ошибка", "Выберите изображение из датасета!")
            return
        
        if not os.path.exists(self.config.lora_path):
            QMessageBox.critical(self, "Ошибка", "LoRA модель не найдена!")
            return
        
        prompt = self.prompt_text.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Ошибка", "Введите промпт!")
            return
        
        # Проверка токена sks
        if "sks" not in prompt:
            reply = QMessageBox.question(
                self,
                "Токен не используется",
                "Вы не использовали токен 'sks'.\nБез него LoRA не будет работать.\n\nДобавить токен?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                prompt = f"sks {prompt}"
                self.prompt_text.setPlainText(prompt)
        
        # Получение параметров
        strength = self.strength_slider.value() / 100.0
        steps = self.steps_slider.value()
        guidance = self.guidance_slider.value() / 2.0
        width = self.width_spin.value()
        height = self.height_spin.value()
        num_variants = self.variants_slider.value()
        
        # Подготовка UI
        self._prepare_ui_for_generation(steps, num_variants)
        
        # Создание и запуск воркера
        self.worker = ImageGenerator(
            lora_path=self.config.lora_path,
            base_model=self.config.base_model,
            txt2img_model=self.config.txt2img_model,
            init_image=self.source_image if self.generation_mode == "img2img" else None,
            prompt=prompt,
            strength=strength,
            steps=steps,
            guidance=guidance,
            width=width,
            height=height,
            mode=self.generation_mode,
            num_variants=num_variants
        )
        
        self.worker.progress.connect(self.status_label.setText)
        self.worker.progress_step.connect(self.update_progress)
        self.worker.images_ready.connect(self.on_images_ready)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.generation_finished)
        self.worker.start()
    
    def _prepare_ui_for_generation(self, steps: int, num_variants: int):
        """Подготовить UI перед генерацией"""
        self.progress_bar.setValue(0)
        self.progress_details.setText(f"Шаг 0/{steps * num_variants} • 0%")
        self.progress_status.setText("🟡 Подготовка к генерации...")
        
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText(f"⏳ Генерация {num_variants} вариантов...")
        self.status_label.setText(f"🎨 Генерация {self.generation_mode} ({num_variants} вариантов)...")
        
        self.variant_selector.setVisible(False)
        self.selected_view_box.setVisible(False)
        self.save_btn.setEnabled(False)
        self.save_all_btn.setEnabled(False)
    
    def update_progress(self, step: int, total: int, percent: int):
        """Обновить прогресс генерации"""
        self.progress_bar.setValue(percent)
        self.progress_details.setText(f"Шаг {step}/{total} • {percent}%")
        
        if percent < 30:
            self.progress_status.setText("🟡 Начало генерации...")
            self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF9800;")
        elif percent < 70:
            self.progress_status.setText("🟢 Генерация в процессе...")
            self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        elif percent < 100:
            self.progress_status.setText("🔵 Финальные штрихи...")
            self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
        else:
            self.progress_status.setText("✅ Генерация завершена!")
            self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
    
    def on_images_ready(self, images: List[Image.Image]):
        """Обработка полученных изображений"""
        self.generated_images = images
        self.selected_variant_index = -1
        
        self.variant_selector.set_variants(images)
        self.variant_selector.setVisible(True)
        
        self.save_all_btn.setEnabled(True)
        self.status_label.setText(f"✅ Сгенерировано {len(images)} вариантов. Выберите лучший!")
    
    def on_variant_selected(self, index: int):
        """Обработка выбора варианта"""
        if 0 <= index < len(self.generated_images):
            self.selected_variant_index = index
            selected_image = self.generated_images[index]
            
            pixmap = pil_to_pixmap(selected_image)
            if not pixmap.isNull():
                zoomed = scale_pixmap(pixmap, 500, 500)
                self.selected_image_label.setPixmap(zoomed)
                self.selected_image_label.setText("")
            
            self.selected_view_box.setVisible(True)
            self.save_btn.setEnabled(True)
            self.status_label.setText(f"✅ Выбран вариант {index + 1}/{len(self.generated_images)}")
    
    def handle_error(self, error: str):
        """Обработка ошибки генерации"""
        QMessageBox.critical(self, "Ошибка", f"Ошибка генерации:\n{error}")
        self.generation_finished()
        self.progress_status.setText("❌ Ошибка генерации")
        self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #f44336;")
    
    def generation_finished(self):
        """Завершение генерации"""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("🎨 СГЕНЕРИРОВАТЬ")
    
    # ========== СОХРАНЕНИЕ ==========
    
    def save(self):
        """Сохранить выбранный вариант"""
        if self.selected_variant_index < 0 or self.selected_variant_index >= len(self.generated_images):
            QMessageBox.warning(self, "Ошибка", "Выберите вариант для сохранения!")
            return
        
        self._save_variant(self.selected_variant_index, single=True)
    
    def save_all(self):
        """Сохранить все варианты"""
        if not self.generated_images:
            QMessageBox.warning(self, "Ошибка", "Нет изображений для сохранения!")
            return
        
        reply = QMessageBox.question(
            self,
            "Сохранить все",
            f"Сохранить все {len(self.generated_images)} вариантов?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for i in range(len(self.generated_images)):
                self._save_variant(i, single=False)
            
            QMessageBox.information(
                self,
                "Сохранено",
                f"✅ Все {len(self.generated_images)} вариантов сохранены!"
            )
            self.status_label.setText(f"✅ Сохранено {len(self.generated_images)} вариантов")
    
    def _save_variant(self, variant_index: int, single: bool = True):
        """Сохранить один вариант"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        mode_prefix = "txt2img" if self.generation_mode == "txt2img" else "img2img"
        result_filename = f"{mode_prefix}_variant{variant_index + 1}_{width}x{height}_{timestamp}.png"
        result_path = os.path.join(self.config.output_dir, result_filename)
        
        self.generated_images[variant_index].save(result_path)
        
        # Сохранить исходное изображение для img2img
        if self.source_image and self.generation_mode == "img2img" and single:
            source_filename = f"{mode_prefix}_source_{width}x{height}_{timestamp}.png"
            source_path = os.path.join(self.config.output_dir, source_filename)
            self.source_image.save(source_path)
        
        # Сохранить метаданные
        if single:
            meta = {
                "mode": self.generation_mode,
                "variant": variant_index + 1,
                "total_variants": len(self.generated_images),
                "prompt": self.prompt_text.toPlainText(),
                "original_prompt": self.original_prompt_text.toPlainText() if self.generation_mode == "img2img" else "",
                "strength": self.strength_slider.value() / 100.0,
                "steps": self.steps_slider.value(),
                "guidance": self.guidance_slider.value() / 2.0,
                "width": width,
                "height": height,
                "timestamp": timestamp
            }
            
            meta_path = os.path.join(
                self.config.output_dir,
                f"{mode_prefix}_meta_variant{variant_index + 1}_{width}x{height}_{timestamp}.json"
            )
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(
                self,
                "Сохранено",
                f"✅ Вариант {variant_index + 1} сохранен:\n{result_path}\n\n"
                f"📝 Промпт: {meta['prompt'][:100]}..."
            )
            
            self.status_label.setText(f"✅ Сохранено: {result_filename}")
    
    # ========== УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ ==========
    
    def zoom_in(self):
        """Увеличить изображение"""
        self.current_zoom = min(self.current_zoom + 0.25, 3.0)
        self.apply_zoom_to_selected()
    
    def zoom_out(self):
        """Уменьшить изображение"""
        self.current_zoom = max(self.current_zoom - 0.25, 0.25)
        self.apply_zoom_to_selected()
    
    def zoom_reset(self):
        """Сбросить зум"""
        self.current_zoom = 1.0
        self.apply_zoom_to_selected()
    
    def apply_zoom_to_selected(self):
        """Применить зум к выбранному изображению"""
        if 0 <= self.selected_variant_index < len(self.generated_images):
            selected_image = self.generated_images[self.selected_variant_index]
            pixmap = pil_to_pixmap(selected_image)
            if not pixmap.isNull():
                zoomed = scale_pixmap(
                    pixmap,
                    int(500 * self.current_zoom),
                    int(500 * self.current_zoom)
                )
                self.selected_image_label.setPixmap(zoomed)
    
    def clear_all(self):
        """Очистить все"""
        self.source_image = None
        self.generated_images = []
        self.selected_variant_index = -1
        self.source_pixmap = None
        
        self.source_image_label.clear()
        if self.generation_mode == "img2img":
            self.source_image_label.setText("Выберите\nизображение\nиз датасета")
        else:
            self.source_image_label.setText("Txt2Img режим\n(изображение\nне требуется)")
        self.source_image_label.setMinimumSize(300, 300)
        
        self.variant_selector.setVisible(False)
        self.selected_view_box.setVisible(False)
        self.selected_image_label.clear()
        self.selected_image_label.setText("Выберите\nвариант\nвыше")
        self.selected_image_label.setMinimumSize(400, 400)
        
        if self.generation_mode == "img2img":
            self.original_prompt_text.clear()
        
        self.generate_btn.setEnabled(self.generation_mode == "txt2img")
        self.save_btn.setEnabled(False)
        self.save_all_btn.setEnabled(False)
        self.status_label.setText("✅ Очищено")
        
        self.progress_bar.setValue(0)
        self.progress_details.setText("Шаг 0/0 • 0%")
        self.progress_status.setText("⚪ Ожидание генерации")
        self.progress_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #666;")
        
        self.current_zoom = 1.0
    
    def open_output_folder(self):
        """Открыть папку с результатами"""
        path = os.path.abspath(self.config.output_dir)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            os.system(f"open '{path}'")
        else:
            os.system(f"xdg-open '{path}'")