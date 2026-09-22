"""
Real curriculum diagrams for a resource (Decision 027), looked up
alongside retrieval evidence so the chat response can show one inline.

Science-only by construction: resource_images only has rows for CK-12
resources the backfill script has processed (Cell Biology in v1) --
math resources simply never match, no subject branching needed here.
"""

import re

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel

_WORD = re.compile(r"[a-z]+")
_MIN_WORD_LENGTH = 4


class ResourceImage(BaseModel):
    source_page_path: str
    source_page_title: str
    public_url: str
    caption: str
    license: str
    attribution: str


async def get_resource_images(pool: AsyncConnectionPool, resource_id: str) -> list[ResourceImage]:
    """Every image backfilled for a resource, ordered for a deterministic fallback pick."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "select source_page_path, source_page_title, public_url, caption, license, attribution "
                "from resource_images where resource_id = %s order by source_page_path",
                (resource_id,),
            )
            rows = await cur.fetchall()
    return [ResourceImage(**row) for row in rows]


def _significant_words(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.lower()) if len(word) >= _MIN_WORD_LENGTH}


def pick_best_image(chunk_content: str, images: list[ResourceImage]) -> ResourceImage | None:
    """
    Choose which of a resource's images (it may have several, one per
    lesson page) actually matches the evidence chunk in hand.

    A resource bundles multiple CK-12 lesson pages into one row with no
    retained page boundary per chunk (see the images.py package
    docstring and Decision 027), so "the resource has an image" doesn't
    mean "this chunk's image" -- score each candidate by how many
    significant words its caption and page title share with the
    chunk's own text, and take the best match. Falls back to the
    lexicographically first page when nothing overlaps, rather than
    picking randomly, so behavior is at least deterministic.
    """
    if not images:
        return None
    if len(images) == 1:
        return images[0]

    ordered = sorted(images, key=lambda image: image.source_page_path)
    chunk_words = _significant_words(chunk_content)
    best_image = ordered[0]
    best_score = -1
    for image in ordered:
        candidate_words = _significant_words(f"{image.caption} {image.source_page_title}")
        score = len(chunk_words & candidate_words)
        if score > best_score:
            best_score = score
            best_image = image
    return best_image
