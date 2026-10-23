from pathlib import Path

from PIL import Image

from app.services.poster_generator import available_templates, generate_poster, load_template
from app.services.validation import clean_text, parse_season, valid_title

ROOT = Path(__file__).resolve().parents[1]


def artwork(tmp_path: Path, size=(300, 900), color=(220, 30, 80, 255)) -> Path:
    path = tmp_path / "artwork.png"
    Image.new("RGBA", size, color).save(path)
    return path


def test_template_configuration_loading():
    image, config = load_template()
    assert image.size == tuple(config["canvas"]) == (1672, 941)
    assert available_templates()[0]["id"] == "template_01"
    assert config["artwork_box"] == [1029, 94, 1633, 856]
    assert config["editable_regions"]["rating"]["box"] == [230, 600, 405, 655]
    assert config["editable_regions"]["studio"]["box"] == [450, 600, 650, 655]
    assert config["editable_regions"]["genres"]["box"] == [680, 600, 915, 655]


def test_season_and_input_validation():
    assert parse_season("season 2") == 2
    assert parse_season("3") == 3
    assert parse_season("season 0") is None
    assert clean_text("  a\n\tb  ") == "a b"
    assert valid_title("Frieren")
    assert not valid_title("")


def test_png_output_and_metadata(tmp_path):
    path = tmp_path / "poster.png"
    generate_poster(artwork(tmp_path), "Frieren: Beyond Journey's End", 1, "A long synopsis that should be wrapped neatly inside the synopsis panel.", rating="8.8/10", studio="Madhouse", genres="Fantasy, Drama", output_path=path)
    result = Image.open(path)
    assert result.format == "PNG"
    assert result.size == (1672, 941)
    assert result.getpixel((1200, 300))[:3] == (220, 30, 80)


def test_aspect_ratios_and_rounded_mask(tmp_path):
    wide = tmp_path / "wide.png"
    generate_poster(artwork(tmp_path, size=(1600, 300), color=(10, 200, 100, 255)), "Long Title " * 8, 12, "Synopsis " * 80, output_path=wide)
    image = Image.open(wide)
    assert image.getpixel((1200, 300))[:3] == (10, 200, 100)
    # The rounded artwork corner remains the template corner rather than the uploaded color.
    assert image.getpixel((1029, 94))[:3] != (10, 200, 100)


def test_optional_metadata_is_neutral(tmp_path):
    path = tmp_path / "optional.png"
    generate_poster(artwork(tmp_path), "Solo Leveling", 2, "Synopsis", rating=None, studio=None, genres=[], output_path=path)
    assert path.exists() and path.stat().st_size > 0


def test_each_supplied_field_is_drawn_once_in_its_designated_region(tmp_path):
    path = tmp_path / "placement.png"
    generate_poster(
        artwork(tmp_path, color=(15, 145, 220, 255)),
        "UNIQUE TITLE",
        7,
        "UNIQUE SYNOPSIS",
        rating="9.7/10",
        studio="UNIQUE STUDIO",
        genres="UNIQUE GENRE",
        output_path=path,
    )
    image = Image.open(path).convert("RGB")
    # Text-bearing pixels must exist in each configured editable box.
    boxes = {
        "title": (220, 73, 965, 190),
        "season": (350, 190, 780, 315),
        "synopsis": (225, 350, 910, 455),
        "rating": (230, 600, 405, 655),
        "studio": (450, 600, 650, 655),
        "genres": (680, 600, 915, 655),
    }
    for name, (x1, y1, x2, y2) in boxes.items():
        crop = image.crop((x1, y1, x2, y2))
        assert len(crop.getcolors(maxcolors=1_000_000)) > 8, name

    # Static labels/icons are copied from the original template, not redrawn or
    # cleared along with the editable values.
    template, _ = load_template()
    template = template.convert("RGB")
    for box in ((220, 550, 415, 610), (445, 550, 650, 610), (650, 550, 925, 610)):
        assert image.crop(box).tobytes() == template.crop(box).tobytes()

    # A one-line sample has no second placeholder-value line below the rendered value.
    assert not any(min(image.getpixel((x, y))) > 180 for y in range(650, 700) for x in range(225, 405))
    assert not any(min(image.getpixel((x, y))) > 180 for y in range(650, 700) for x in range(445, 650))
    assert not any(min(image.getpixel((x, y))) > 180 for y in range(650, 700) for x in range(675, 925))

    # The artwork stays inside the measured image box and does not cover the left metadata panel.
    assert image.getpixel((1200, 300)) == (15, 145, 220)
    assert image.getpixel((1000, 300)) != (15, 145, 220)
