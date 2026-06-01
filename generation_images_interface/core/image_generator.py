import torch
from PyQt5.QtCore import QThread, pyqtSignal
from diffusers import StableDiffusionImg2ImgPipeline, StableDiffusionPipeline
from peft import PeftModel
from PIL import Image
from typing import List, Optional

class ImageGenerator(QThread):
    """Поток для генерации нескольких вариантов изображений"""
    
    progress = pyqtSignal(str)
    progress_step = pyqtSignal(int, int, int)
    images_ready = pyqtSignal(object)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(
        self,
        lora_path: str,
        base_model: str,
        txt2img_model: str,
        init_image: Optional[Image.Image] = None,
        prompt: str = "",
        strength: float = 0.75,
        steps: int = 30,
        guidance: float = 7.5,
        width: int = 512,
        height: int = 512,
        mode: str = "img2img",
        num_variants: int = 4
    ):
        super().__init__()
        self.lora_path = lora_path
        self.base_model = base_model
        self.txt2img_model = txt2img_model
        self.init_image = init_image
        self.prompt = prompt
        self.strength = strength
        self.steps = steps
        self.guidance = guidance
        self.width = width
        self.height = height
        self.mode = mode
        self.num_variants = num_variants
        
    def run(self):
        """Основной метод потока"""
        try:
            self.progress.emit("⏳ Загрузка модели...")
            self.progress_step.emit(0, self.steps * self.num_variants, 0)
            
            pipe = self._load_pipeline()
            pipe = self._load_lora(pipe)
            pipe = pipe.to("cuda")
            pipe.enable_attention_slicing()
            
            self.progress.emit(f"🎨 Генерация {self.num_variants} вариантов {self.width}x{self.height}...")
            
            init_image = self._prepare_init_image()
            generated_images = self._generate_variants(pipe, init_image)
            
            self.progress.emit("✅ Все варианты готовы!")
            total_steps = self.steps * self.num_variants
            self.progress_step.emit(total_steps, total_steps, 100)
            self.images_ready.emit(generated_images)
            self.finished.emit()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def _load_pipeline(self):
        """Загрузить соответствующий пайплайн"""
        if self.mode == "txt2img":
            return StableDiffusionPipeline.from_pretrained(
                self.txt2img_model,
                torch_dtype=torch.float16,
                safety_checker=None
            )
        else:
            return StableDiffusionImg2ImgPipeline.from_pretrained(
                self.base_model,
                torch_dtype=torch.float16,
                safety_checker=None
            )
    
    def _load_lora(self, pipe):
        """Загрузить LoRA веса"""
        self.progress.emit("🔧 Загрузка LoRA весов...")
        pipe.unet = PeftModel.from_pretrained(pipe.unet, self.lora_path)
        return pipe
    
    def _prepare_init_image(self) -> Optional[Image.Image]:
        """Подготовить начальное изображение для img2img"""
        if self.mode == "img2img" and self.init_image:
            img = self.init_image.convert("RGB")
            return img.resize((self.width, self.height))
        return None
    
    def _generate_variants(self, pipe, init_image: Optional[Image.Image]) -> List[Image.Image]:
        """Сгенерировать варианты изображений"""
        generated_images = []
        total_steps = self.steps * self.num_variants
        current_step = 0
        
        for variant in range(self.num_variants):
            self.progress.emit(f"🎨 Вариант {variant + 1}/{self.num_variants}")
            
            def progress_callback(step, timestep, latents):
                nonlocal current_step
                current_step = variant * self.steps + step
                progress_percent = int((current_step / total_steps) * 100)
                self.progress_step.emit(current_step, total_steps, progress_percent)
                self.progress.emit(f"🎨 Вариант {variant + 1}: Шаг {step}/{self.steps} ({progress_percent}%)")
                return True
            
            with torch.autocast("cuda"):
                result = self._run_inference(pipe, init_image, progress_callback)
                generated_images.append(result.images[0])
        
        return generated_images
    
    def _run_inference(self, pipe, init_image, callback):
        """Запустить инференс в зависимости от режима"""
        if self.mode == "txt2img":
            return pipe(
                prompt=self.prompt,
                num_inference_steps=self.steps,
                guidance_scale=self.guidance,
                width=self.width,
                height=self.height,
                callback=callback,
                callback_steps=1
            )
        else:
            return pipe(
                prompt=self.prompt,
                image=init_image,
                strength=self.strength,
                num_inference_steps=self.steps,
                guidance_scale=self.guidance,
                callback=callback,
                callback_steps=1
            )