from __future__ import annotations

import base64

from openai import OpenAI

from .base import ImageInput, ModelProvider


MAX_RESPONSE_PARTS = 4
CONTINUATION_PROMPT = """Continue the previous response exactly where it stopped.
Do not repeat text that was already returned. Finish every remaining required section.
Return only the continuation of the document or answer, with no preamble."""


def _incomplete_reason(response) -> str | None:
    details = getattr(response, "incomplete_details", None)
    if isinstance(details, dict):
        return details.get("reason")
    return getattr(details, "reason", None)


class OpenAIProvider(ModelProvider):
    def __init__(self, api_key: str, model: str, max_output_tokens: int):
        super().__init__(model, max_output_tokens)
        self.client = OpenAI(api_key=api_key)

    def generate(self, system: str, prompt: str, images: list[ImageInput] | None = None) -> str:
        content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
        for image in images or []:
            encoded = base64.b64encode(image.data).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{image.mime_type};base64,{encoded}",
                }
            )
        response = self.client.responses.create(
            model=self.model,
            instructions=system,
            input=[{"role": "user", "content": content}],  # type: ignore[list-item]
            max_output_tokens=self.max_output_tokens,
        )
        parts: list[str] = []
        for part_number in range(MAX_RESPONSE_PARTS):
            parts.append(response.output_text or "")
            if getattr(response, "status", "completed") != "incomplete":
                return "".join(parts)

            reason = _incomplete_reason(response)
            if reason != "max_output_tokens":
                raise RuntimeError(f"The model returned an incomplete response ({reason or 'unknown reason'}). No partial output was saved.")
            if part_number == MAX_RESPONSE_PARTS - 1:
                raise RuntimeError(
                    "The model output exceeded the configured limit after multiple continuations. "
                    "Increase RAISE_MAX_OUTPUT_TOKENS or use a model with a larger output limit. No partial output was saved."
                )

            response = self.client.responses.create(
                model=self.model,
                instructions=system,
                previous_response_id=response.id,
                input=CONTINUATION_PROMPT,
                max_output_tokens=self.max_output_tokens,
            )

        raise RuntimeError("The model response could not be completed. No partial output was saved.")

