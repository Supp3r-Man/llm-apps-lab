"""Compose the final social preview: AI background plus crisp text drawn by Pillow.

The model draws only the background. The repository name and description are
rendered here, so the spelling is always exact.
"""

import io
import re

from PIL import Image, ImageDraw, ImageFont

PREVIEW_SIZE = (1280, 640)  # GitHub's recommended social preview size

BOLD_FONTS = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc", "LiberationSans-Bold.ttf"]
REGULAR_FONTS = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc", "LiberationSans-Regular.ttf"]


def load_font(size: int, bold: bool = False):
    for name in BOLD_FONTS if bold else REGULAR_FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def crop_to_size(png: bytes, size: tuple[int, int]) -> Image.Image:
    """Center-crop to the target aspect ratio, then resize."""
    image = Image.open(io.BytesIO(png)).convert("RGB")
    target_ratio = size[0] / size[1]
    if image.width / image.height > target_ratio:
        new_width = round(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = round(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))
    return image.resize(size, Image.LANCZOS)


def _pieces(text: str):
    """Yield (piece, separator). Words may also break after - _ / and . so repo names wrap."""
    for word in text.split():
        parts = [p for p in re.split(r"(?<=[-_/.])", word) if p]
        for i, part in enumerate(parts):
            yield part, (" " if i == len(parts) - 1 else "")


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    """Greedy wrap. Overflow is cut with an ellipsis on the last line."""
    lines: list[str] = []
    current = ""
    for piece, sep in _pieces(text):
        trial = current + piece
        if draw.textlength(trial, font=font) <= max_width or not current.strip():
            current = trial + sep
        else:
            lines.append(current.rstrip())
            current = piece + sep
    if current.strip():
        lines.append(current.rstrip())
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def ellipsize(draw: ImageDraw.ImageDraw, line: str, font, max_width: int) -> str:
    """Cut a line that still does not fit (e.g. one long unbreakable word)."""
    if draw.textlength(line, font=font) <= max_width:
        return line
    while line and draw.textlength(line + "…", font=font) > max_width:
        line = line[:-1]
    return line.rstrip() + "…"


def _scrim(size: tuple[int, int]) -> Image.Image:
    """Dark gradient on the left so text stays readable on any background."""
    width, height = size
    strip = Image.new("L", (width, 1))
    fade_end = int(width * 0.8)
    strip.putdata([max(0, round(215 * (1 - x / fade_end))) if x < fade_end else 0 for x in range(width)])
    mask = strip.resize((width, height))
    black = Image.new("RGBA", size, (0, 0, 0, 0))
    black.putalpha(mask)
    return black


def compose_preview(
    background_png: bytes,
    title: str,
    subtitle: str = "",
    meta: str = "",
    size: tuple[int, int] = PREVIEW_SIZE,
) -> bytes:
    width, height = size
    image = crop_to_size(background_png, size).convert("RGBA")
    image = Image.alpha_composite(image, _scrim(size))
    draw = ImageDraw.Draw(image)

    margin = round(width * 0.06)
    text_width = round(width * 0.56)

    # Shrink the title until all of it fits in two lines within the text column.
    # Lines cut with an ellipsis always fit the width, so completeness is checked too.
    title_size = round(height * 0.16)
    while True:
        title_font = load_font(title_size, bold=True)
        title_lines = wrap(draw, title, title_font, text_width, max_lines=2)
        complete = "".join(title_lines).replace(" ", "") == title.replace(" ", "")
        fits = complete and all(draw.textlength(line, font=title_font) <= text_width for line in title_lines)
        if fits or title_size <= 32:
            break
        title_size -= 4

    title_lines = [ellipsize(draw, line, title_font, text_width) for line in title_lines]

    sub_font = load_font(round(height * 0.058))
    sub_lines = wrap(draw, subtitle, sub_font, text_width, max_lines=3) if subtitle else []
    sub_lines = [ellipsize(draw, line, sub_font, text_width) for line in sub_lines]

    title_h = round(title_size * 1.15)
    sub_h = round(height * 0.058 * 1.4)
    block_h = len(title_lines) * title_h + (round(height * 0.04) + len(sub_lines) * sub_h if sub_lines else 0)
    y = (height - block_h) // 2

    for line in title_lines:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255, 255))
        y += title_h
    if sub_lines:
        y += round(height * 0.04)
        for line in sub_lines:
            draw.text((margin, y), line, font=sub_font, fill=(225, 230, 240, 255))
            y += sub_h
    if meta:
        draw.text((margin, height - margin - round(height * 0.05)), meta, font=load_font(round(height * 0.045)), fill=(190, 198, 215, 255))

    out = io.BytesIO()
    image.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
