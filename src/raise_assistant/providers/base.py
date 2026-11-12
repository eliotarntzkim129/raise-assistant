from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str


class ModelProvider(ABC):
    def __init__(self, model: str, max_output_tokens: int):
        self.model = model
        self.max_output_tokens = max_output_tokens

    @abstractmethod
    def generate(self, system: str, prompt: str, images: list[ImageInput] | None = None) -> str:
        raise NotImplementedError

    def test(self) -> str:
        return self.generate(
            "You are a connection test. Follow the instruction exactly.",
            "Reply with exactly: CONNECTION_OK",
        ).strip()

