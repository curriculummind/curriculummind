"""Unit tests for curriculum-image filtering and selection (Decision 027)."""

from bs4 import BeautifulSoup

from app.retrieval.images import ResourceImage, pick_best_image
from scripts.backfill_resource_images import is_decorative_image, select_genuine_diagram


def _img(html: str):
    return BeautifulSoup(html, "html.parser").find("img")


def test_empty_alt_is_decorative() -> None:
    assert is_decorative_image("https://example.com/x.png", "") is True


def test_placeholder_alt_is_decorative() -> None:
    assert is_decorative_image("https://example.com/x.png", "alt") is True


def test_logo_src_is_decorative_regardless_of_alt() -> None:
    assert is_decorative_image("https://cdn.libretexts.net/Logos/k12_full.png", "Library homepage") is True


def test_ck12_badge_src_is_decorative() -> None:
    assert is_decorative_image("https://www.ck12.org/media/common/images/logo_ck12.svg", "CK-12 Foundation") is True


def test_genuine_diagram_is_not_decorative() -> None:
    assert is_decorative_image("https://dr282zn36sxxg.cloudfront.net/x", "Organelles of a eukaryotic cell") is False


def test_select_genuine_diagram_skips_leading_decorative_images() -> None:
    tags = [
        _img('<img src="https://cdn.libretexts.net/Logos/k12_full.png" alt="Library homepage">'),
        _img('<img src="https://example.com/placeholder.png" alt="alt">'),
        _img('<img src="https://example.com/real.jpg" alt="Position of the nucleus inside a cell">'),
        _img('<img src="https://www.ck12.org/media/images/ck12-license.svg" alt="CK-12 Foundation">'),
    ]
    result = select_genuine_diagram(tags)
    assert result is not None
    assert result["alt"] == "Position of the nucleus inside a cell"


def test_select_genuine_diagram_returns_none_when_everything_is_decorative() -> None:
    tags = [
        _img('<img src="https://cdn.libretexts.net/Logos/k12_full.png" alt="Library homepage">'),
        _img('<img src="https://example.com/placeholder.png" alt="">'),
    ]
    assert select_genuine_diagram(tags) is None


def _image(caption: str, page: str = "page") -> ResourceImage:
    return ResourceImage(
        source_page_path=page,
        source_page_title=page,
        public_url=f"https://example.com/{page}.jpg",
        caption=caption,
        license="test",
        attribution="test",
    )


def test_pick_best_image_returns_none_for_empty_list() -> None:
    assert pick_best_image("some chunk text", []) is None


def test_pick_best_image_returns_the_only_image() -> None:
    image = _image("Organelles of a eukaryotic cell")
    assert pick_best_image("anything", [image]) is image


def test_pick_best_image_prefers_the_caption_that_overlaps_the_chunk() -> None:
    nucleus = _image("Position of the nucleus inside a cell", page="a-nucleus")
    membrane = _image("Drawing of a plasma membrane", page="b-membrane")
    chunk = "The nucleus is often called the control center of the cell."
    assert pick_best_image(chunk, [membrane, nucleus]) is nucleus


def test_pick_best_image_falls_back_to_first_page_when_nothing_overlaps() -> None:
    a = _image("Organelles of a eukaryotic cell", page="a-page")
    b = _image("Features of a plant cell", page="b-page")
    chunk = "Completely unrelated text about something else entirely."
    assert pick_best_image(chunk, [b, a]) is a
