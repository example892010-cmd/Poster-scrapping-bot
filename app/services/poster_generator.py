from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "templates"
FONTS_DIR = ROOT / "assets" / "fonts"


def load_template(template_id: str = "template_01") -> tuple[Image.Image, dict]:
    directory = TEMPLATES_DIR / template_id
    with (directory / "config.json").open(encoding="utf-8") as handle:
        config = json.load(handle)
    image = Image.open(directory / "template.png").convert("RGBA")
    expected = tuple(config["canvas"])
    if image.size != expected:
        raise ValueError(f"Template canvas {image.size} does not match config {expected}")
    return image, config


def available_templates() -> list[dict]:
    result = []
    for directory in sorted(TEMPLATES_DIR.glob("template_*")):
        if (directory / "template.png").exists() and (directory / "config.json").exists():
            with (directory / "config.json").open(encoding="utf-8") as handle:
                result.append(json.load(handle))
    return result


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS_DIR / name), size=size)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, family: str, max_size: int, min_size: int, width: int) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -1):
        font = _font(family, size)
        if draw.textbbox((0, 0), text, font=font, stroke_width=0)[2] <= width:
            return font
    return _font(family, min_size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _clear_with_soft_patch(base: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Clear placeholder text using a clean local strip and a soft blend."""
    x1, y1, x2, y2 = box
    strip = base.crop((170, y1, 205, y2)).resize((x2 - x1, y2 - y1), Image.Resampling.BICUBIC)
    base.alpha_composite(strip.filter(ImageFilter.GaussianBlur(radius=6)), dest=(x1, y1))


def _panel(base: Image.Image, box: tuple[int, int, int, int], fill=(5, 16, 28, 230), radius=18) -> None:
    x1, y1, x2, y2 = box
    overlay = Image.new("RGBA", (x2 - x1, y2 - y1), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle((0, 0, x2 - x1 - 1, y2 - y1 - 1), radius=radius, fill=fill)
    base.alpha_composite(overlay, dest=(x1, y1))


def _opaque_rect(base: Image.Image, box: tuple[int, int, int, int], fill=(5, 16, 28, 255)) -> None:
    x1, y1, x2, y2 = box
    base.alpha_composite(Image.new("RGBA", (x2 - x1, y2 - y1), fill), dest=(x1, y1))


def _paste_artwork(base: Image.Image, artwork: Image.Image, config: dict, decorative_circle: Image.Image) -> None:
    x1, y1, x2, y2 = config["artwork_box"]
    width, height = x2 - x1, y2 - y1
    fitted = ImageOps.fit(artwork.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=config["artwork_radius"], fill=255)
    base.alpha_composite(Image.composite(fitted, Image.new("RGBA", fitted.size), mask), dest=(x1, y1))
    # Restore the template's separate circular decorative element exactly as supplied.
    cx1, cy1, cx2, cy2 = config["decorative_circle"]
    circle_mask = Image.new("L", decorative_circle.size, 0)
    ImageDraw.Draw(circle_mask).ellipse((0, 0, decorative_circle.width - 1, decorative_circle.height - 1), fill=255)
    base.alpha_composite(Image.composite(decorative_circle, Image.new("RGBA", decorative_circle.size), circle_mask), dest=(cx1, cy1))


def generate_poster(
    artwork_path: str | Path,
    title: str,
    season: int | str,
    synopsis: str,
    rating: str | None = None,
    studio: str | None = None,
    genres: Iterable[str] | str = (),
    template_id: str = "template_01",
    output_path: str | Path | None = None,
) -> Image.Image:
    template, config = load_template(template_id)
    # Keep a pristine copy for the decorative circle that sits over the artwork area.
    circle_box = tuple(config["decorative_circle"])
    circle = template.crop(circle_box)
    base = template.copy()
    draw = ImageDraw.Draw(base)

    # Remove only editable placeholder regions; all permanent branding and controls remain intact.
    _clear_with_soft_patch(base, (180, 54, 1000, 324))
    draw = ImageDraw.Draw(base)
    _panel(base, (225, 366, 970, 462), fill=(5, 16, 28, 235))
    _panel(base, (225, 516, 975, 657), fill=(5, 16, 28, 235))
    _opaque_rect(base, (225, 348, 970, 375))
    for region in ((225, 560, 410, 657), (450, 560, 650, 657), (680, 560, 970, 657)):
        _opaque_rect(base, region)
    draw = ImageDraw.Draw(base)

    title_box = config["title_box"]
    title_font = _fit_font(draw, title.upper(), "PosterNarrow-Bold.otf", 105, 42, title_box[2] - title_box[0])
    title_w = draw.textbbox((0, 0), title.upper(), font=title_font, stroke_width=2)[2]
    title_x = title_box[0] + max(0, (title_box[2] - title_box[0] - title_w) // 2)
    draw.text((title_x, title_box[1]), title.upper(), font=title_font, fill=config["colors"]["white"], stroke_width=3, stroke_fill=config["colors"]["title_outline"])

    season_text = f"SEASON {season}"
    season_font = _fit_font(draw, season_text, "PosterNarrow-Bold.otf", 98, 40, 560)
    season_w = draw.textbbox((0, 0), season_text, font=season_font)[2]
    draw.text((430 - season_w // 2, 202), season_text, font=season_font, fill=config["colors"]["white"])

    synopsis_font = _font("PosterSans-Regular.otf", 26)
    synopsis_lines = _wrap(draw, synopsis, synopsis_font, 690)
    for index, line in enumerate(synopsis_lines[:3]):
        draw.text((245, 380 + index * 28), line, font=synopsis_font, fill=config["colors"]["white"])

    rating_value = rating.strip() if rating and rating.strip() else "—"
    studio_value = studio.strip() if studio and studio.strip() else "—"
    genre_text = ", ".join(g.strip() for g in genres if g.strip()) if not isinstance(genres, str) else genres.strip()
    genre_value = genre_text or "—"
    label_font = _font("PosterSans-Bold.otf", 18)
    value_font = _font("PosterSans-Bold.otf", 27)
    small_font = _font("PosterSans-Regular.otf", 20)
    draw.text((285, 535), "IMDb RATING", font=label_font, fill=config["colors"]["white"])
    draw.text((300, 575), rating_value, font=value_font, fill=config["colors"]["white"])
    draw.text((505, 535), "STUDIO", font=label_font, fill=config["colors"]["white"])
    studio_lines = _wrap(draw, studio_value, small_font, 185)
    for index, line in enumerate(studio_lines[:2]):
        draw.text((500, 580 + index * 24), line, font=small_font, fill=config["colors"]["white"])
    draw.text((765, 535), "GENRES", font=label_font, fill=config["colors"]["white"])
    genre_lines = _wrap(draw, genre_value, small_font, 190)
    for index, line in enumerate(genre_lines[:3]):
        draw.text((735, 580 + index * 24), line, font=small_font, fill=config["colors"]["white"])

    artwork = Image.open(artwork_path)
    _paste_artwork(base, artwork, config, circle)
    result = base.convert("RGB")
    if output_path:
        result.save(output_path, format="PNG", optimize=True)
    return result
