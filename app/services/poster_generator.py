from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "templates"
FONTS_DIR = ROOT / "assets" / "fonts"


def _template_directory(template_id: str) -> Path:
    """Resolve both the original and currently tracked template layouts."""
    candidates = (TEMPLATES_DIR / template_id, TEMPLATES_DIR / template_id / template_id)
    for directory in candidates:
        if (directory / "config.json").is_file() and (directory / "template.png").is_file():
            return directory
    raise FileNotFoundError(f"Template assets not found for {template_id}")


def load_template(template_id: str = "template_01") -> tuple[Image.Image, dict]:
    directory = _template_directory(template_id)
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
        try:
            resolved = _template_directory(directory.name)
        except FileNotFoundError:
            continue
        with (resolved / "config.json").open(encoding="utf-8") as handle:
            result.append(json.load(handle))
    return result


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in (FONTS_DIR, FONTS_DIR / "fonts"):
        path = directory / name
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    raise FileNotFoundError(f"Font asset not found: {name}")


def _box_size(box: list[int] | tuple[int, int, int, int]) -> tuple[int, int]:
    return box[2] - box[0], box[3] - box[1]


def _fit_font(draw: ImageDraw.ImageDraw, text: str, family: str, max_size: int, min_size: int, width: int) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -1):
        font = _font(family, size)
        if draw.textbbox((0, 0), text, font=font, stroke_width=0)[2] <= width:
            return font
    return _font(family, min_size)


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Wrap without changing words or punctuation supplied by the user."""
    lines: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if not current or draw.textbbox((0, 0), candidate, font=font)[2] <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines or [""]


def _clear_editable_region(base: Image.Image, pristine: Image.Image, region: dict) -> None:
    """Replace only a placeholder-value region with a clean local template patch."""
    box = tuple(region.get("clear_box", region["box"]))
    if region.get("fill"):
        base.alpha_composite(
            Image.new("RGBA", _box_size(box), ImageColor.getcolor(region["fill"], "RGBA")),
            dest=(box[0], box[1]),
        )
        return
    source = tuple(region["source"])
    patch = pristine.crop(source).resize(_box_size(box), Image.Resampling.BICUBIC)
    # A small blur removes source-edge seams while retaining the template's local lighting.
    base.alpha_composite(patch.filter(ImageFilter.GaussianBlur(radius=1.5)), dest=(box[0], box[1]))


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, box: tuple[int, int, int, int], fill: str, stroke_width: int = 0, stroke_fill: str | None = None) -> None:
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    x = x1 + max(0, (x2 - x1 - (bbox[2] - bbox[0])) // 2) - bbox[0]
    y = y1 + max(0, (y2 - y1 - (bbox[3] - bbox[1])) // 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def _draw_wrapped_centered(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, box: tuple[int, int, int, int], fill: str, line_gap: int = 3) -> None:
    x1, y1, x2, y2 = box
    lines = _wrap_lines(draw, text, font, x2 - x1)
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
    total_height = sum(line_heights) + line_gap * max(0, len(lines) - 1)
    y = y1 + max(0, (y2 - y1 - total_height) // 2)
    for line, height in zip(lines, line_heights):
        _draw_centered(draw, line, font, (x1, y, x2, y + height), fill)
        y += height + line_gap


def _paste_artwork(base: Image.Image, artwork: Image.Image, config: dict, decorative_circle: Image.Image) -> None:
    x1, y1, x2, y2 = config["artwork_box"]
    width, height = x2 - x1, y2 - y1
    fitted = ImageOps.fit(artwork.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=config["artwork_radius"], fill=255)
    base.alpha_composite(Image.composite(fitted, Image.new("RGBA", fitted.size), mask), dest=(x1, y1))

    # Restore the original circular decorative element without restoring its rectangular crop.
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
    pristine = template.copy()
    base = template.copy()
    regions = config["editable_regions"]

    # Clear each editable value exactly once. Static labels, icons, dividers, borders,
    # branding, buttons, and effects remain supplied by the original template.
    for region in regions.values():
        _clear_editable_region(base, pristine, region)

    # The labels, icons, and dividers are permanent template artwork. Restore their
    # exact original pixels after clearing the lower value zones.
    for header_box in ((220, 510, 415, 610), (445, 510, 650, 610), (650, 510, 925, 610)):
        base.alpha_composite(pristine.crop(header_box), dest=(header_box[0], header_box[1]))

    draw = ImageDraw.Draw(base)
    white = config["colors"]["white"]
    title_box = tuple(config["title_box"])
    title_font = _fit_font(draw, title, "PosterNarrow-Bold.otf", 104, 38, title_box[2] - title_box[0] - 20)
    _draw_centered(draw, title, title_font, title_box, white, stroke_width=3, stroke_fill=config["colors"]["title_outline"])

    season_box = tuple(config["season_box"])
    season_text = f"SEASON {season}"
    season_font = _fit_font(draw, season_text, "PosterNarrow-Bold.otf", 96, 38, season_box[2] - season_box[0] - 20)
    _draw_centered(draw, season_text, season_font, season_box, white)

    synopsis_box = tuple(regions["synopsis"]["box"])
    synopsis_font = _font("PosterSans-Regular.otf", 26)
    _draw_wrapped_centered(draw, synopsis, synopsis_font, (synopsis_box[0] + 15, synopsis_box[1] + 6, synopsis_box[2] - 15, synopsis_box[3] - 6), white, line_gap=4)

    rating_box = tuple(regions["rating"]["box"])
    studio_box = tuple(regions["studio"]["box"])
    genres_box = tuple(regions["genres"]["box"])
    if rating:
        rating_font = _fit_font(draw, rating, "PosterSans-Bold.otf", 42, 22, rating_box[2] - rating_box[0] - 8)
        _draw_centered(draw, rating, rating_font, rating_box, white)
    if studio:
        studio_font = _font("PosterSans-Regular.otf", 21)
        _draw_wrapped_centered(draw, studio, studio_font, studio_box, white, line_gap=2)
    if isinstance(genres, str):
        genre_text = genres
    else:
        genre_text = ", ".join(genres)
    if genre_text:
        genres_font = _font("PosterSans-Regular.otf", 20)
        _draw_wrapped_centered(draw, genre_text, genres_font, genres_box, white, line_gap=2)

    with Image.open(artwork_path) as artwork:
        _paste_artwork(base, artwork, config, pristine.crop(tuple(config["decorative_circle"])))

    result = base.convert("RGB")
    if output_path:
        result.save(output_path, format="PNG", optimize=True)
    return result
