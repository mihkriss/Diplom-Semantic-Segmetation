import os

class Config:
    """Конфигурация приложения"""
    lora_path = "./lora_sks_building768_02/lora_final"
    dataset_path = "./768.02/images"
    metadata_file = "./768.02/metadata.jsonl"
    base_model = "runwayml/stable-diffusion-v1-5"
    txt2img_model = "runwayml/stable-diffusion-v1-5"
    output_dir = "./lora_dataset_generations"
    
    @classmethod
    def ensure_output_dir(cls):
        """Создать директорию для вывода если не существует"""
        os.makedirs(cls.output_dir, exist_ok=True)
        return cls.output_dir