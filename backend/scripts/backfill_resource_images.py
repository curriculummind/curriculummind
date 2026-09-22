"""
Backfill real diagram images for CK-12 science resources (Decision
027) -- a separate, additive, re-runnable operation from
ingest_content.py, not entangled with it. Existing curriculum_resources
and document_chunks rows are never touched; this only adds rows to the
new resource_images table and objects to the curriculum-images Storage
bucket.

v1 scope is deliberately narrow: only the resources named in
TARGET_CONCEPT_SLUGS are processed, proving out the image-selection
heuristic on a small, already-spot-checked corpus (Cell Biology)
before trusting it more broadly. Extending later is adding more slugs
here, not a redesign.

Run with: python -m scripts.backfill_resource_images
"""

import os
import re
import sys

import httpx
import psycopg
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ingest_content import BROWSER_HEADERS, LIBRETEXTS_BASE, RESOURCES  # noqa: E402
from supabase import create_client  # noqa: E402

load_dotenv()

TARGET_CONCEPT_SLUGS = {"cell-structure-and-function"}

STORAGE_BUCKET = "curriculum-images"
ATTRIBUTION = "CK-12 Foundation, via K12 LibreTexts"

# Confirmed by direct inspection of real CK-12/LibreTexts pages: these
# are the site-chrome images every lesson page carries, not diagrams.
_DECORATIVE_SRC_SUBSTRINGS = ("cdn.libretexts.net/Logos/", "ck12.org/media/")
_DECORATIVE_ALT_VALUES = {
    "",
    "alt",
    "k12 libretexts",
    "library homepage",
    "ck12 foundation",
    "ck12 foundation is licensed under ck12 curriculum materials license",
}


def is_decorative_image(src: str, alt: str | None) -> bool:
    """True for site chrome (logos, attribution badges, empty/placeholder alt) -- false for a real diagram."""
    normalized_alt = (alt or "").strip().lower()
    if normalized_alt in _DECORATIVE_ALT_VALUES:
        return True
    return any(substring in src for substring in _DECORATIVE_SRC_SUBSTRINGS)


def select_genuine_diagram(img_tags: list[Tag]) -> Tag | None:
    """The first non-decorative <img> in document order, or None if every candidate is chrome."""
    for tag in img_tags:
        src = tag.get("src") or ""
        alt = tag.get("alt")
        if src and not is_decorative_image(src, alt):
            return tag
    return None


def full_resolution_url(src: str) -> str:
    """CK-12's CDN serves a smaller variant by default; swapping the size token gives the full image."""
    return src.replace("IMAGE_TINY", "IMAGE")


def fetch_page_html(path: str) -> BeautifulSoup | None:
    """Fetch one lesson page and return its main-content soup, scoped the same way load_libretexts_page is."""
    response = httpx.get(LIBRETEXTS_BASE + path, headers=BROWSER_HEADERS, follow_redirects=True, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find(id="elm-main-content")


_CONTENT_TYPE_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}


def storage_path(concept_slug: str, page_path: str, content_type: str) -> str:
    """A deterministic, human-legible Storage object path for one lesson page's image."""
    slug = re.sub(r"[^a-z0-9]+", "-", page_path.lower()).strip("-")
    ext = _CONTENT_TYPE_EXTENSIONS.get(content_type, ".jpg")
    return f"{concept_slug}/{slug}{ext}"


def find_resource_id(cur: psycopg.Cursor, title: str) -> str:
    """Look up an already-ingested resource by its exact title -- the only correlatable key today."""
    cur.execute("select id from curriculum_resources where title = %s", (title,))
    rows = cur.fetchall()
    if len(rows) != 1:
        raise ValueError(f"expected exactly one curriculum_resources row titled {title!r}, found {len(rows)}")
    return str(rows[0][0])


def main() -> None:
    storage_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    bucket = storage_client.storage.from_(STORAGE_BUCKET)

    conn = psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None)
    try:
        with conn.cursor() as cur:
            targets = [
                r for r in RESOURCES if r["kind"] == "libretexts" and r["concept_slug"] in TARGET_CONCEPT_SLUGS
            ]
            for resource in targets:
                print(f"Backfilling images: {resource['title']}")
                resource_id = find_resource_id(cur, resource["title"])

                for page_title, page_path in resource["pages"]:
                    main_content = fetch_page_html(page_path)
                    if main_content is None:
                        print(f"  {page_title}: no main content, skipping")
                        continue

                    img_tags = main_content.find_all("img")
                    diagram = select_genuine_diagram(img_tags)
                    if diagram is None:
                        print(f"  {page_title}: no genuine diagram found")
                        continue

                    survivors = [
                        t for t in img_tags if t.get("src") and not is_decorative_image(t["src"], t.get("alt"))
                    ]
                    if len(survivors) > 1:
                        print(f"  {page_title}: {len(survivors)} candidates survived filtering, using the first")

                    image_url = full_resolution_url(diagram["src"])
                    caption = (diagram.get("alt") or "").strip()

                    image_response = httpx.get(
                        image_url, headers=BROWSER_HEADERS, follow_redirects=True, timeout=30
                    )
                    image_response.raise_for_status()
                    content_type = image_response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                    path = storage_path(resource["concept_slug"], page_path, content_type)
                    bucket.upload(
                        path, image_response.content, file_options={"upsert": "true", "content-type": content_type}
                    )
                    public_url = bucket.get_public_url(path)

                    cur.execute(
                        """
                        insert into resource_images
                            (resource_id, source_page_path, source_page_title, image_url,
                             public_url, caption, license, attribution)
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (resource_id, source_page_path) do update set
                            source_page_title = excluded.source_page_title,
                            image_url = excluded.image_url,
                            public_url = excluded.public_url,
                            caption = excluded.caption,
                            license = excluded.license,
                            attribution = excluded.attribution
                        """,
                        (
                            resource_id,
                            page_path,
                            page_title,
                            image_url,
                            public_url,
                            caption,
                            resource["license"],
                            ATTRIBUTION,
                        ),
                    )
                    conn.commit()
                    print(f"  {page_title}: stored ({caption!r})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
