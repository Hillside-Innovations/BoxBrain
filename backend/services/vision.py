"""Describe/caption images to get searchable text. Mock or BLIP (open-source)."""
from pathlib import Path
from typing import List

from config import settings


class VisionService:
    _model = None  # lazy-load BLIP

    def _get_model(self):
        if VisionService._model is not None:
            return VisionService._model
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        if torch.cuda.is_available():
            model = model.to("cuda")
        VisionService._model = (processor, model)
        return VisionService._model

    def describe_frames(self, frame_paths: List[Path]) -> List[str]:
        """Return one text description per frame (objects/contents) for embedding."""
        if settings.mock_vision:
            return [f"box contents frame {i+1}" for i in range(len(frame_paths))]
        processor, model = self._get_model()
        import torch
        from PIL import Image
        descriptions = []
        for path in frame_paths:
            image = Image.open(path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            out = model.generate(**inputs, max_length=50)
            text = processor.decode(out[0], skip_special_tokens=True)
            descriptions.append(text)
        return descriptions
