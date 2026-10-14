"""Thin wrapper around the Gemini Interactions API for Nano Banana image models."""

import base64
import io
import os
from dataclasses import dataclass

from PIL import Image

DEFAULT_MODEL = os.getenv("NANOBANANA_MODEL", "gemini-nano-banana-2.1")

# Model IDs listed in Google's image generation docs. Not every model supports
# every aspect ratio or size, so API errors are surfaced to the user as-is.
MODELS = {
    "Nano Banana 2.1": "gemini-nano-banana-2.1",
    "Nano Banana Pro": "gemini-3-pro-image",
    "Nano Banana 2": "gemini-3.1-flash-image",
    "Nano Banana 2 Lite (fastest)": "gemini-3.1-flash-lite-image",
}


class ImageGenerationError(RuntimeError):
    """Raised with a message that is safe to show to the user."""


@dataclass
class GeneratedImage:
    png: bytes
    interaction_id: str | None


def _decode(data) -> bytes:
    """Return image bytes from base64 text or from bytes the SDK may have decoded already."""
    if isinstance(data, str):
        attempts = [lambda: base64.b64decode(data)]
    else:
        raw = bytes(data)
        attempts = [lambda: raw, lambda: base64.b64decode(raw)]
    for attempt in attempts:
        try:
            decoded = attempt()
            Image.open(io.BytesIO(decoded)).verify()
            return decoded
        except Exception:
            continue
    raise ImageGenerationError("The API returned image data that could not be decoded.")


def explain_error(exc: Exception) -> str:
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    detail = str(exc).strip().splitlines()[0][:300] if str(exc).strip() else type(exc).__name__
    if code in (401, 403):
        return f"The API key was rejected or has no access to this model ({code}). {detail}"
    if code == 404:
        return f"Model not found ({code}). Pick another model in the sidebar. {detail}"
    if code == 429:
        return f"Rate limit or quota reached ({code}). Wait a moment and try again. {detail}"
    return f"Image generation failed. {detail}"


def generate_image(
    client,
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
    previous_interaction_id: str | None = None,
) -> GeneratedImage:
    """Generate an image, or edit the previous one when previous_interaction_id is given."""
    body = {
        "model": model,
        "input": prompt,
        "response_format": {
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
        },
    }
    if previous_interaction_id:
        body["previous_interaction_id"] = previous_interaction_id
    try:
        interaction = client.interactions.create(**body)
    except Exception as exc:
        raise ImageGenerationError(explain_error(exc)) from exc

    image = getattr(interaction, "output_image", None)
    if image is None or not getattr(image, "data", None):
        said = getattr(interaction, "output_text", None)
        raise ImageGenerationError("The model returned no image." + (f" It said: {said}" if said else ""))
    return GeneratedImage(_decode(image.data), getattr(interaction, "id", None))


def fit_to_width(png: bytes, width: int) -> bytes:
    """Resize to the given width, keeping the aspect ratio."""
    image = Image.open(io.BytesIO(png)).convert("RGB")
    height = round(image.height * width / image.width)
    out = io.BytesIO()
    image.resize((width, height), Image.LANCZOS).save(out, format="PNG", optimize=True)
    return out.getvalue()
