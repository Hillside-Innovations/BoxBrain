"""Describe/caption images to get searchable text. Mock or BLIP (open-source)."""
import logging
from pathlib import Path
from typing import List

from config import settings

logger = logging.getLogger(__name__)

# Fallback when a frame cannot be described (corrupt, too dark, BLIP empty, etc.)
_FALLBACK_CAPTION = "box contents"

# Strong prompt to force BLIP to name specific items (e.g. "winter coats, scarves") not generic scene ("a pile of clothes")
_CAPTION_PROMPT = "This box contains "
_MAX_CAPTION_LENGTH = 72
_NUM_BEAMS = 4


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
        """Return one text description per frame (objects/contents) for embedding.
        Failed or empty frames get a fallback caption so the pipeline never crashes and we always return one description per frame.
        """
        if not frame_paths:
            return []
        if settings.mock_vision:
            return [f"box contents frame {i+1}" for i in range(len(frame_paths))]
        processor, model = self._get_model()
        import torch
        from PIL import Image
        descriptions: List[str] = []
        for i, path in enumerate(frame_paths):
            try:
                if not path.exists():
                    logger.warning("Vision: frame path does not exist %s", path)
                    descriptions.append(_FALLBACK_CAPTION)
                    continue
                image = Image.open(path).convert("RGB")
                inputs = processor(images=image, text=_CAPTION_PROMPT, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.to("cuda") for k, v in inputs.items()}
                out = model.generate(
                    **inputs,
                    max_length=_MAX_CAPTION_LENGTH,
                    num_beams=_NUM_BEAMS,
                )
                text = (processor.decode(out[0], skip_special_tokens=True) or "").strip()
                if not text:
                    logger.debug("Vision: BLIP returned empty caption for frame %s", path.name)
                    text = _FALLBACK_CAPTION
                descriptions.append(text)
            except Exception as e:
                logger.warning("Vision: failed to describe frame %s: %s", path, e, exc_info=False)
                descriptions.append(_FALLBACK_CAPTION)
        if descriptions and all(d.strip().lower() == _FALLBACK_CAPTION for d in descriptions):
            logger.warning(
                "Vision: all %d frame(s) used fallback caption (no specific objects detected). Check lighting and video quality.",
                len(descriptions),
            )
        return descriptions
