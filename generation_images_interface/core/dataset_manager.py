import os
import json
from typing import Optional, List, Dict, Any

class DatasetManager:
    """Менеджер для работы с датасетом"""
    
    def __init__(self, metadata_file: str, image_folder: str):
        self.metadata_file = metadata_file
        self.image_folder = image_folder
        self.samples: List[Dict[str, Any]] = []
        self.load_metadata()
        
    def load_metadata(self) -> None:
        """Загрузить метаданные из файла"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        data['file_name'] = os.path.basename(data['file_name'])
                        self.samples.append(data)
                print(f"✅ Загружено {len(self.samples)} образцов из датасета")
            else:
                print(f"⚠️ Файл метаданных не найден: {self.metadata_file}")
        except Exception as e:
            print(f"❌ Ошибка загрузки метаданных: {e}")
    
    def get_sample(self, index: int) -> Optional[Dict[str, Any]]:
        """Получить образец по индексу"""
        if 0 <= index < len(self.samples):
            return self.samples[index]
        return None
    
    def get_image_path(self, index: int) -> Optional[str]:
        """Получить путь к изображению по индексу"""
        sample = self.get_sample(index)
        if not sample:
            return None
            
        possible_paths = [
            os.path.join(self.image_folder, sample['file_name']),
            os.path.join("./training_img", sample['file_name'])
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def get_prompt(self, index: int) -> str:
        """Получить промпт для образца"""
        sample = self.get_sample(index)
        if sample:
            return sample.get('text', '')
        return ''
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def is_empty(self) -> bool:
        return len(self.samples) == 0