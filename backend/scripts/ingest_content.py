"""
One-time ingestion script for the M0 seed corpus: Grade 6 Math and
Science content from EngageNY/Eureka Math (Great Minds) and CK-12 (via
the K12 LibreTexts mirror, which serves the same CK-12-licensed content
as server-rendered HTML rather than CK-12's own JavaScript-only site).

Each source is fetched directly and parsed mechanically (pypdf for PDF,
BeautifulSoup for HTML) -- no AI summarization or paraphrasing touches
the stored text, so what lands in document_chunks is the actual source
material, not a model's rendition of it. See architecture §15 and
Decision 013.

Run with: python -m scripts.ingest_content
"""

import asyncio
import io
import os
import re
import sys

import httpx
import psycopg
import pypdf
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.providers.embeddings import OpenAIEmbeddingClient  # noqa: E402

load_dotenv()

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    )
}

ENGAGENY_LICENSE = "CC BY-NC-SA 3.0 US (Great Minds / EngageNY) -- non-commercial use only, see Decision 013"
CK12_LICENSE = "CC BY-NC 3.0 (CK-12 Foundation, via K12 LibreTexts) -- non-commercial use only, see Decision 013"

RESOURCES = [
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "ratios-and-unit-rates",
        "concept_name": "Ratios and Unit Rates",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 1: Ratios and Unit Rates (Teacher Edition, Module Overview and Topic A)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M1_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (6, 25),
        "standards": ["6.RP.A.1", "6.RP.A.2", "6.RP.A.3"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4: Expressions and Equations (Teacher Edition, Module Overview and Topic A)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (6, 25),
        "standards": ["6.EE.A.4", "6.EE.B.5", "6.EE.B.6", "6.EE.B.7"],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "cell-structure-and-function",
        "concept_name": "Cell Structure and Function",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Cell Biology (Cell Theory through Plant Cell Structure)",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/02%3A_Cell_Biology",
        "kind": "libretexts",
        "pages": [
            ("2.18: Cell Theory", "02%3A_Cell_Biology/2.18%3A_Cell_Theory"),
            ("2.19: Prokaryotic and Eukaryotic Cells", "02%3A_Cell_Biology/2.19%3A_Prokaryotic_and_Eukaryotic_Cells"),
            ("2.20: Cell Membrane", "02%3A_Cell_Biology/2.20%3A_Cell_Membrane"),
            ("2.21: Nucleus", "02%3A_Cell_Biology/2.21%3A_Nucleus"),
            ("2.22: Organelles", "02%3A_Cell_Biology/2.22%3A_Organelles"),
            ("2.23: Plant Cell Structure", "02%3A_Cell_Biology/2.23%3A_Plant_Cell_Structure"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "ecosystems-and-interactions",
        "concept_name": "Ecosystems and Interactions",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Ecology (Ecosystems through Energy Flow)",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/12%3A_Ecology",
        "kind": "libretexts",
        "pages": [
            ("12.10: Ecosystems", "12%3A_Ecology/12.10%3A_Ecosystems"),
            ("12.11: Habitat and Niche", "12%3A_Ecology/12.11%3A_Habitat_and_Niche"),
            ("12.16: Producer", "12%3A_Ecology/12.16%3A_Producer"),
            ("12.17: Consumers and Decomposers", "12%3A_Ecology/12.17%3A_Consumers_and_Decomposers"),
            ("12.18: Food Chain", "12%3A_Ecology/12.18%3A_Food_Chain"),
            ("12.19: Energy Flow", "12%3A_Ecology/12.19%3A_Energy_Flow"),
        ],
        "standards": [],
    },
]

LIBRETEXTS_BASE = "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/"


def load_pdf_text(url: str, page_range: tuple[int, int]) -> str:
    """Download a PDF and extract text from an inclusive page range."""
    response = httpx.get(url, timeout=60)
    response.raise_for_status()
    reader = pypdf.PdfReader(io.BytesIO(response.content))
    start, end = page_range
    pages = [reader.pages[i].extract_text() for i in range(start, min(end, len(reader.pages)))]
    return "\n\n".join(pages)


def load_libretexts_page(path: str) -> str:
    """Fetch one K12 LibreTexts lesson page and return its cleaned body text."""
    response = httpx.get(LIBRETEXTS_BASE + path, headers=BROWSER_HEADERS, follow_redirects=True, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    main = soup.find(id="elm-main-content")
    if main is None:
        return ""
    raw = main.get_text("\n", strip=True)
    lines = [
        line
        for line in raw.split("\n")
        if "newcommand" not in line and not line.strip().startswith("\\(")
    ]
    text = "\n".join(lines)
    text = re.sub(r"^(Last updated|Save as PDF|Page ID|\d+)$", "", text, flags=re.MULTILINE)
    return text.strip()


def clean_text(text: str) -> str:
    """Normalize whitespace left over from PDF/HTML extraction."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, target_chars: int = 1000) -> list[str]:
    """Split cleaned text into paragraph-aware chunks near target_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 20]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) > target_chars:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        chunks.append(current.strip())
    return chunks


def ensure_subject(cur: psycopg.Cursor, slug: str, name: str) -> str:
    """Insert a subject if it doesn't exist yet and return its id."""
    cur.execute(
        "insert into subjects (slug, name) values (%s, %s) "
        "on conflict (slug) do update set name = excluded.name returning id",
        (slug, name),
    )
    return cur.fetchone()[0]


def ensure_concept(cur: psycopg.Cursor, subject_id: str, slug: str, name: str, grade_band: str) -> str:
    """Insert a concept if it doesn't exist yet and return its id."""
    cur.execute(
        "insert into concepts (subject_id, slug, name, grade_band) values (%s, %s, %s, %s) "
        "on conflict (subject_id, slug) do update set name = excluded.name returning id",
        (subject_id, slug, name, grade_band),
    )
    return cur.fetchone()[0]


def ensure_standards(cur: psycopg.Cursor, concept_id: str, codes: list[str]) -> None:
    """Link Common Core standard codes to a concept, creating the framework/standard rows as needed."""
    if not codes:
        return
    cur.execute(
        "insert into curriculum_frameworks (slug, name, country) values "
        "('us-common-core-math', 'Common Core State Standards -- Mathematics', 'US') "
        "on conflict (slug) do nothing"
    )
    cur.execute("select id from curriculum_frameworks where slug = 'us-common-core-math'")
    framework_id = cur.fetchone()[0]
    for code in codes:
        cur.execute(
            "insert into standards (framework_id, code) values (%s, %s) "
            "on conflict (framework_id, code) do nothing returning id",
            (framework_id, code),
        )
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "select id from standards where framework_id = %s and code = %s",
                (framework_id, code),
            )
            row = cur.fetchone()
        cur.execute(
            "insert into concept_standards (concept_id, standard_id) values (%s, %s) "
            "on conflict do nothing",
            (concept_id, row[0]),
        )


def insert_resource(cur: psycopg.Cursor, concept_id: str, resource: dict) -> str:
    """Insert a curriculum_resources row and return its id."""
    cur.execute(
        "insert into curriculum_resources (concept_id, source, license, source_url, title, grade_band) "
        "values (%s, %s, %s, %s, %s, %s) returning id",
        (
            concept_id,
            resource["source"],
            resource["license"],
            resource["source_url"],
            resource["title"],
            resource["grade_band"],
        ),
    )
    return cur.fetchone()[0]


async def embed_and_insert_chunks(
    cur: psycopg.Cursor, resource_id: str, chunks: list[str], embedder: OpenAIEmbeddingClient
) -> None:
    """Embed each chunk and insert it as a document_chunks row."""
    vectors = await embedder.embed(chunks)
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        cur.execute(
            "insert into document_chunks (resource_id, chunk_index, content, embedding) "
            "values (%s, %s, %s, %s)",
            (resource_id, index, chunk, str(vector)),
        )


async def main() -> None:
    """Ingest every configured resource: fetch, clean, chunk, embed, store."""
    embedder = OpenAIEmbeddingClient(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            for resource in RESOURCES:
                print(f"Ingesting: {resource['title']}")

                if resource["kind"] == "pdf":
                    raw = load_pdf_text(resource["source_url"], resource["page_range"])
                elif resource["kind"] == "libretexts":
                    parts = [load_libretexts_page(path) for _, path in resource["pages"]]
                    raw = "\n\n".join(p for p in parts if p)
                else:
                    raise ValueError(f"unknown kind: {resource['kind']}")

                text = clean_text(raw)
                chunks = chunk_text(text)
                print(f"  {len(text)} chars -> {len(chunks)} chunks")

                subject_id = ensure_subject(cur, resource["subject_slug"], resource["subject_name"])
                concept_id = ensure_concept(
                    cur, subject_id, resource["concept_slug"], resource["concept_name"], resource["grade_band"]
                )
                ensure_standards(cur, concept_id, resource["standards"])
                resource_id = insert_resource(cur, concept_id, resource)
                await embed_and_insert_chunks(cur, resource_id, chunks, embedder)
                conn.commit()
                print("  done")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
