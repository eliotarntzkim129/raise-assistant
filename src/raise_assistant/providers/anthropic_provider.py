from __future__ import annotations

import base64

from anthropic import Anthropic, AnthropicVertex

from .base import ImageInput, ModelProvider


def _content(prompt: str, images: list[ImageInput] | None) -> list[dict]:
    content: list[dict] = []
    for image in images or []:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.mime_type,
                    "data": base64.b64encode(image.data).decode("ascii"),
                },
            }
        )
    content.append({"type": "text", "text": prompt})
    return content


def _text_from_message(message) -> str:
    return "\n".join(block.text for block in message.content if getattr(block, "type", "") == "text")


class AnthropicProvider(ModelProvider):
    def __init__(self, api_key: str, model: str, max_output_tokens: int):
        super().__init__(model, max_output_tokens)
        self.client = Anthropic(api_key=api_key)

    def generate(self, system: str, prompt: str, images: list[ImageInput] | None = None) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_output_tokens,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": _content(prompt, images)}],
        )
        return _text_from_message(response)


class VertexClaudeProvider(ModelProvider):
    def __init__(self, project_id: str, region: str, model: str, max_output_tokens: int):
        super().__init__(model, max_output_tokens)
        self.client = AnthropicVertex(project_id=project_id, region=region)

    def generate(self, system: str, prompt: str, images: list[ImageInput] | None = None) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_output_tokens,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": _content(prompt, images)}],
        )
        return _text_from_message(response)

