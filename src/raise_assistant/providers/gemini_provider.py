from __future__ import annotations

from google import genai
from google.genai import types

from .base import ImageInput, ModelProvider


class GeminiProvider(ModelProvider):
    def __init__(
        self,
        *,
        model: str,
        max_output_tokens: int,
        api_key: str | None = None,
        project: str | None = None,
        location: str | None = None,
    ):
        super().__init__(model, max_output_tokens)
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client(vertexai=True, project=project, location=location)

    def generate(self, system: str, prompt: str, images: list[ImageInput] | None = None) -> str:
        contents: list = [prompt]
        for image in images or []:
            contents.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,
                max_output_tokens=self.max_output_tokens,
            ),
        )
        return response.text or ""

