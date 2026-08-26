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
        "title": "Eureka Math Grade 6 Module 1, Topic A: Representing and Reasoning About Ratios (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M1_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (15, 66),
        "standards": ["6.RP.A.1", "6.RP.A.3a"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "ratios-and-unit-rates",
        "concept_name": "Ratios and Unit Rates",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 1, Topic B: Collections of Equivalent Ratios (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M1_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (66, 135),
        "standards": ["6.RP.A.3a"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "ratios-and-unit-rates",
        "concept_name": "Ratios and Unit Rates",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 1, Topic C: Unit Rates (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M1_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (135, 190),
        "standards": ["6.RP.A.2", "6.RP.A.3b", "6.RP.A.3d"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "ratios-and-unit-rates",
        "concept_name": "Ratios and Unit Rates",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 1, Topic D: Percent (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M1_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (190, 232),
        "standards": ["6.RP.A.3c"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "arithmetic-operations-fractions-decimals",
        "concept_name": "Arithmetic Operations Including Division of Fractions",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 2, Topic A: Dividing Fractions by Fractions (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M2_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (9, 88),
        "standards": ["6.NS.A.1"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "arithmetic-operations-fractions-decimals",
        "concept_name": "Arithmetic Operations Including Division of Fractions",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 2, Topic B: Multi-Digit Decimal Operations (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M2_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (88, 117),
        "standards": ["6.NS.B.3"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "arithmetic-operations-fractions-decimals",
        "concept_name": "Arithmetic Operations Including Division of Fractions",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 2, Topic C: Dividing Whole Numbers and Decimals (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M2_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (117, 164),
        "standards": ["6.NS.B.2", "6.NS.B.3"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "arithmetic-operations-fractions-decimals",
        "concept_name": "Arithmetic Operations Including Division of Fractions",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 2, Topic D: Number Theory (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M2_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (164, 206),
        "standards": ["6.NS.B.4"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "rational-numbers",
        "concept_name": "Rational Numbers",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 3, Topic A: Understanding Positive and Negative Numbers on the Number Line (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M3_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (10, 61),
        "standards": ["6.NS.C.5", "6.NS.C.6a", "6.NS.C.6c"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "rational-numbers",
        "concept_name": "Rational Numbers",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 3, Topic B: Order and Absolute Value (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M3_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (61, 140),
        "standards": ["6.NS.C.6c", "6.NS.C.7"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "rational-numbers",
        "concept_name": "Rational Numbers",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 3, Topic C: Rational Numbers and the Coordinate Plane (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M3_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (140, 185),
        "standards": ["6.NS.C.6b", "6.NS.C.6c", "6.NS.C.8"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic A: Relationships of the Operations (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (13, 50),
        "standards": ["6.EE.A.3"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic B: Special Notations of Operations (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (50, 73),
        "standards": ["6.EE.A.1", "6.EE.A.2c"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic C: Replacing Letters and Numbers (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (73, 97),
        "standards": ["6.EE.A.2c", "6.EE.A.4"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic D: Expanding, Factoring, and Distributing Expressions (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (97, 154),
        "standards": ["6.EE.A.2a", "6.EE.A.2b", "6.EE.A.3", "6.EE.A.4"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic E: Expressing Operations in Algebraic Form (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (154, 180),
        "standards": ["6.EE.A.2a", "6.EE.A.2b"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic F: Writing and Evaluating Expressions and Formulas (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (192, 239),
        "standards": ["6.EE.A.2a", "6.EE.A.2c", "6.EE.B.6"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic G: Solving Equations (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (239, 330),
        "standards": ["6.EE.B.5", "6.EE.B.6", "6.EE.B.7"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "expressions-and-equations",
        "concept_name": "Expressions and Equations",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 4, Topic H: Applications of Equations (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M4_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (330, 377),
        "standards": ["6.EE.B.5", "6.EE.B.6", "6.EE.B.7", "6.EE.B.8", "6.EE.C.9"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "area-surface-area-volume",
        "concept_name": "Area, Surface Area, and Volume Problems",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 5, Topic A: Area of Triangles, Quadrilaterals, and Polygons (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M5_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (11, 92),
        "standards": ["6.G.A.1"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "area-surface-area-volume",
        "concept_name": "Area, Surface Area, and Volume Problems",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 5, Topic B: Polygons on the Coordinate Plane (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M5_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (92, 142),
        "standards": ["6.G.A.3"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "area-surface-area-volume",
        "concept_name": "Area, Surface Area, and Volume Problems",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 5, Topic C: Volume of Right Rectangular Prisms (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M5_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (150, 212),
        "standards": ["6.G.A.2"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "area-surface-area-volume",
        "concept_name": "Area, Surface Area, and Volume Problems",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 5, Topic D: Nets and Surface Area (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M5_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (212, 317),
        "standards": ["6.G.A.2", "6.G.A.4"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "statistics",
        "concept_name": "Statistics",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 6, Topic A: Understanding Distributions (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M6_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (9, 64),
        "standards": ["6.SP.A.1", "6.SP.A.2", "6.SP.B.4", "6.SP.B.5b"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "statistics",
        "concept_name": "Statistics",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 6, Topic B: Summarizing a Distribution That Is Approximately Symmetric Using the Mean and MAD (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M6_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (64, 130),
        "standards": ["6.SP.A.2", "6.SP.A.3", "6.SP.B.4", "6.SP.B.5"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "statistics",
        "concept_name": "Statistics",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 6, Topic C: Summarizing a Distribution That Is Skewed Using the Median and IQR (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M6_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (146, 203),
        "standards": ["6.SP.A.2", "6.SP.A.3", "6.SP.B.4", "6.SP.B.5"],
    },
    {
        "subject_slug": "math",
        "subject_name": "Mathematics",
        "concept_slug": "statistics",
        "concept_name": "Statistics",
        "grade_band": "6",
        "source": "engageny-eureka-math",
        "license": ENGAGENY_LICENSE,
        "title": "Eureka Math Grade 6 Module 6, Topic D: Summarizing and Describing Distributions (Teacher Edition)",
        "source_url": "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Teacher_Editions/G6_TeacherEditions/EM_G6_M6_TeacherEdition.pdf",
        "kind": "pdf",
        "page_range": (203, 240),
        "standards": ["6.SP.B.4", "6.SP.B.5"],
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
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "introduction-to-life-science",
        "concept_name": "Introduction to Life Science",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Introduction to Life Science",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/01%3A_Introduction_to_Life_Science",
        "kind": "libretexts",
        "pages": [
            ("1.1: Scientific Ways of Thinking", "01%3A_Introduction_to_Life_Science/1.01%3A_Scientific_Ways_of_Thinking"),
            ("1.2: Fields in the Life Sciences", "01%3A_Introduction_to_Life_Science/1.02%3A_Fields_in_the_Life_Sciences"),
            ("1.3: Scientific Method", "01%3A_Introduction_to_Life_Science/1.03%3A_Scientific_Method"),
            ("1.4: Scientific Theories", "01%3A_Introduction_to_Life_Science/1.04%3A_Scientific_Theories"),
            ("1.5: Basic and Applied Science", "01%3A_Introduction_to_Life_Science/1.05%3A_Basic_and_Applied_Science"),
            ("1.6: Microscope", "01%3A_Introduction_to_Life_Science/1.06%3A_Microscope"),
            ("1.7: Safety in the Life Sciences", "01%3A_Introduction_to_Life_Science/1.07%3A_Safety_in_the_Life_Sciences"),
            ("1.8: Characteristics of Life", "01%3A_Introduction_to_Life_Science/1.08%3A_Characteristics_of_Life"),
            ("1.9: Organization of Living Things", "01%3A_Introduction_to_Life_Science/1.09%3A_Organization_of_Living_Things"),
            ("1.10: Domain", "01%3A_Introduction_to_Life_Science/1.11%3A_Domain"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "genetics-and-molecular-biology",
        "concept_name": "Genetics and Molecular Biology",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Genetics and Molecular Biology",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/03%3A_Molecular_Biology_and_Genetics",
        "kind": "libretexts",
        "pages": [
            ("3.1: Mutation", "03%3A_Molecular_Biology_and_Genetics/3.01%3A_Mutation"),
            ("3.2: Molecular Genetics Overview", "03%3A_Molecular_Biology_and_Genetics/3.02%3A_Molecular_Genetics_Overview"),
            ("3.3: Pedigree", "03%3A_Molecular_Biology_and_Genetics/3.03%3A_Pedigree"),
            ("3.4: Sex-linked Inheritance", "03%3A_Molecular_Biology_and_Genetics/3.04%3A_Sex-linked_Inheritance"),
            ("3.5: Non-Mendelian Inheritance", "03%3A_Molecular_Biology_and_Genetics/3.05%3A_Non-Mendelian_Inheritance"),
            ("3.6: Polygenic Traits", "03%3A_Molecular_Biology_and_Genetics/3.06%3A_Polygenic_Traits"),
            ("3.7: Genetic Disorders", "03%3A_Molecular_Biology_and_Genetics/3.07%3A_Genetic_Disorders"),
            ("3.8: Recombinant DNA", "03%3A_Molecular_Biology_and_Genetics/3.08%3A_Recombinant_DNA"),
            ("3.9: Cloning", "03%3A_Molecular_Biology_and_Genetics/3.09%3A_Cloning"),
            ("3.10: Human Genome", "03%3A_Molecular_Biology_and_Genetics/3.10%3A_Human_Genome"),
            ("3.11: Pea Plants", "03%3A_Molecular_Biology_and_Genetics/3.11%3A_Pea_Plants"),
            ("3.12: Gene Therapy", "03%3A_Molecular_Biology_and_Genetics/3.12%3A_Gene_Therapy"),
            ("3.13: Agriculture", "03%3A_Molecular_Biology_and_Genetics/3.13%3A_Agriculture"),
            ("3.14: Mendel's Laws", "03%3A_Molecular_Biology_and_Genetics/3.14%3A_Mendel's_Laws"),
            ("3.15: Punnett Squares", "03%3A_Molecular_Biology_and_Genetics/3.15%3A_Punnett_Squares"),
            ("3.16: DNA", "03%3A_Molecular_Biology_and_Genetics/3.16%3A_DNA"),
            ("3.17: DNA Structure and Replication", "03%3A_Molecular_Biology_and_Genetics/3.17%3A_DNA_Structure_and_Replication"),
            ("3.18: RNA", "03%3A_Molecular_Biology_and_Genetics/3.18%3A_RNA"),
            ("3.19: Protein Synthesis", "03%3A_Molecular_Biology_and_Genetics/3.19%3A_Protein_Synthesis"),
            ("3.20: Transcription", "03%3A_Molecular_Biology_and_Genetics/3.20%3A_Transcription"),
            ("3.21: Translation", "03%3A_Molecular_Biology_and_Genetics/3.21%3A_Translation"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "evolution-and-natural-selection",
        "concept_name": "Evolution and Natural Selection",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Evolution and Natural Selection",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/04%3A_Evolution",
        "kind": "libretexts",
        "pages": [
            ("4.1: Theory of Evolution", "04%3A_Evolution/4.01%3A_Theory_of_Evolution"),
            ("4.2: Influences on Darwin", "04%3A_Evolution/4.02%3A_Influences_on_Darwin"),
            ("4.3: Natural Selection", "04%3A_Evolution/4.03%3A_Natural_Selection"),
            ("4.4: Fossils", "04%3A_Evolution/4.04%3A_Fossils"),
            ("4.5: Evolution Evidence", "04%3A_Evolution/4.05%3A_Evolution_Evidence"),
            ("4.6: Molecular Evidence", "04%3A_Evolution/4.06%3A_Molecular_Evidence"),
            ("4.7: Microevolution and Macroevolution", "04%3A_Evolution/4.07%3A_Microevolution_and_Macroevolution"),
            ("4.8: Hardy-Weinberg", "04%3A_Evolution/4.08%3A_Hardy-Weinberg"),
            ("4.9: Origin of Species", "04%3A_Evolution/4.09%3A_Origin_of_Species"),
            ("4.10: Tracing Evolution", "04%3A_Evolution/4.10%3A_Tracing_Evolution"),
            ("4.11: First Cell", "04%3A_Evolution/4.11%3A_First_Cell"),
            ("4.12: Geological Time Scale", "04%3A_Evolution/4.12%3A_Geological_Time_Scale"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "viruses-and-bacteria",
        "concept_name": "Viruses and Bacteria",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Viruses and Bacteria",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/05%3A_Viruses_and_Prokaryotes",
        "kind": "libretexts",
        "pages": [
            ("5.1: Viruses", "05%3A_Viruses_and_Prokaryotes/5.01%3A_Section_1-"),
            ("5.2: Bacteria Characteristics", "05%3A_Viruses_and_Prokaryotes/5.02%3A_Section_2-"),
            ("5.3: Bacteria Nutrition", "05%3A_Viruses_and_Prokaryotes/5.03%3A_Section_3-"),
            ("5.4: Bacteria Reproduction", "05%3A_Viruses_and_Prokaryotes/5.04%3A_Section_4-"),
            ("5.5: Bacteria and Humans", "05%3A_Viruses_and_Prokaryotes/5.05%3A_Section_5-"),
            ("5.6: Archaea", "05%3A_Viruses_and_Prokaryotes/5.06%3A_Section_6-"),
            ("5.7: Types of Archaea", "05%3A_Viruses_and_Prokaryotes/5.7%3A_Types_of_Archaea"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "protists-and-fungi",
        "concept_name": "Protists and Fungi",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Protists and Fungi",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/06%3A_Protists_and_Fungi",
        "kind": "libretexts",
        "pages": [
            ("6.1: Protist Characteristics", "06%3A_Protists_and_Fungi/6.01%3A_Section_1-"),
            ("6.2: Protist Nutrition", "06%3A_Protists_and_Fungi/6.02%3A_Section_2-"),
            ("6.3: Protozoa", "06%3A_Protists_and_Fungi/6.03%3A_Section_3-"),
            ("6.4: Algae", "06%3A_Protists_and_Fungi/6.04%3A_Section_4-"),
            ("6.5: Mold", "06%3A_Protists_and_Fungi/6.05%3A_Section_5-"),
            ("6.6: Importance of Protists", "06%3A_Protists_and_Fungi/6.06%3A_Section_6-"),
            ("6.7: Fungi", "06%3A_Protists_and_Fungi/6.07%3A_Fungi"),
            ("6.8: Fungi Structure", "06%3A_Protists_and_Fungi/6.08%3A_Fungi_Structure"),
            ("6.9: Fungi Reproduction", "06%3A_Protists_and_Fungi/6.09%3A_Fungi_Reproduction"),
            ("6.10: Fungi Classification", "06%3A_Protists_and_Fungi/6.10%3A_Fungi_Classification"),
            ("6.11: Fungi Symbiosis", "06%3A_Protists_and_Fungi/6.11%3A_Fungi_Symbiosis"),
            ("6.12: Use of Fungi", "06%3A_Protists_and_Fungi/6.12%3A_Use_of_Fungi"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "plant-biology",
        "concept_name": "Plant Biology",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Plant Biology",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/07%3A_Plants",
        "kind": "libretexts",
        "pages": [
            ("7.1: Plant Characteristics", "07%3A_Plants/7.01%3A_Section_1-"),
            ("7.2: Plant Evolution", "07%3A_Plants/7.02%3A_Section_2-"),
            ("7.3: Plant Reproduction and Life Cycle", "07%3A_Plants/7.03%3A_Section_3-"),
            ("7.4: Plant Classification", "07%3A_Plants/7.04%3A_Section_4-"),
            ("7.5: Nonvascular Plants", "07%3A_Plants/7.05%3A_Section_5-"),
            ("7.6: Vascular Plants", "07%3A_Plants/7.06%3A_Section_6-"),
            ("7.7: Life Cycle of Seedless Vascular Plants", "07%3A_Plants/7.07%3A_Life_Cycle_of_Seedless_Vascular_Plants"),
            ("7.8: Importance of Plants", "07%3A_Plants/7.08%3A_Importance_of_Plants"),
            ("7.9: Seed Dispersal", "07%3A_Plants/7.09%3A_Seed_Dispersal"),
            ("7.10: Seed Plants", "07%3A_Plants/7.10%3A_Seed_Plants"),
            ("7.11: Angiosperm", "07%3A_Plants/7.11%3A_Angiosperm"),
            ("7.12: Plant Hormones", "07%3A_Plants/7.12%3A_Plant_Hormones"),
            ("7.13: Tropisms", "07%3A_Plants/7.13%3A_Tropisms"),
            ("7.14: Plant Adaptations", "07%3A_Plants/7.14%3A_Plant_Adaptations"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "animal-behavior",
        "concept_name": "Animal Behavior",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Animal Behavior",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/08%3A_Animals",
        "kind": "libretexts",
        "pages": [
            ("8.1: Animal Behavior", "08%3A_Animals/8.01%3A_Section_1-"),
            ("8.2: Innate Behavior", "08%3A_Animals/8.02%3A_Section_2-"),
            ("8.3: Learned Behavior", "08%3A_Animals/8.03%3A_Section_3-"),
            ("8.4: Social Behavior", "08%3A_Animals/8.04%3A_Section_4-"),
            ("8.5: Cyclic Behavior", "08%3A_Animals/8.05%3A_Section_5-"),
            ("8.6: Reproductive Behavior", "08%3A_Animals/8.06%3A_Section_6-"),
            ("8.7: Communication", "08%3A_Animals/8.7%3A_Communication"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "invertebrate-diversity",
        "concept_name": "Invertebrate Diversity",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Invertebrate Diversity",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/09%3A_Invertebrates",
        "kind": "libretexts",
        "pages": [
            ("9.1: Invertebrate Diversity", "09%3A_Invertebrates/9.01%3A_Section_1-"),
            ("9.2: Sponges", "09%3A_Invertebrates/9.02%3A_Section_2-"),
            ("9.3: Cnidarians", "09%3A_Invertebrates/9.03%3A_Section_3-"),
            ("9.4: Flatworms", "09%3A_Invertebrates/9.04%3A_Section_4-"),
            ("9.5: Segmented Worms", "09%3A_Invertebrates/9.05%3A_Section_5-"),
            ("9.6: Roundworms", "09%3A_Invertebrates/9.06%3A_Section_6-"),
            ("9.7: Mollusks", "09%3A_Invertebrates/9.07%3A_Mollusks"),
            ("9.8: Types of Mollusks", "09%3A_Invertebrates/9.08%3A_Types_of_Mollusks"),
            ("9.9: Importance of Mollusks", "09%3A_Invertebrates/9.09%3A_Importance_of_Mollusks"),
            ("9.10: Arthropods", "09%3A_Invertebrates/9.10%3A_Arthropods"),
            ("9.11: Crustaceans", "09%3A_Invertebrates/9.11%3A_Crustaceans"),
            ("9.12: Centipedes and Millipedes", "09%3A_Invertebrates/9.12%3A_Centipedes_and_Millipedes"),
            ("9.13: Arachnids", "09%3A_Invertebrates/9.13%3A_Arachnids"),
            ("9.14: Importance of Arthropods", "09%3A_Invertebrates/9.14%3A_Importance_of_Arthropods"),
            ("9.15: Insects", "09%3A_Invertebrates/9.15%3A_Insects"),
            ("9.16: Insect Food", "09%3A_Invertebrates/9.16%3A_Insect_Food"),
            ("9.17: Insect Reproduction", "09%3A_Invertebrates/9.17%3A_Insect_Reproduction"),
            ("9.18: Importance of Insects", "09%3A_Invertebrates/9.18%3A_Importance_of_Insects"),
            ("9.20: Echinoderms", "09%3A_Invertebrates/9.20%3A_Echinoderms"),
            ("9.21: Types of Echinoderms", "09%3A_Invertebrates/9.21%3A_Types_of_Echinoderms"),
            ("9.22: Importance of Echinoderms", "09%3A_Invertebrates/9.22%3A_Importance_of_Echinoderms"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "vertebrate-diversity",
        "concept_name": "Vertebrate Diversity",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Vertebrate Diversity",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/10%3A_Vertebrates",
        "kind": "libretexts",
        "pages": [
            ("10.1: Chordates", "10%3A_Vertebrates/10.01%3A_Section_1-"),
            ("10.2: Vertebrate Diversity", "10%3A_Vertebrates/10.02%3A_Section_2-"),
            ("10.3: Fish", "10%3A_Vertebrates/10.03%3A_Section_3-"),
            ("10.4: Jawless Fish", "10%3A_Vertebrates/10.04%3A_Section_4-"),
            ("10.5: Cartilaginous Fish", "10%3A_Vertebrates/10.05%3A_Section_5-"),
            ("10.6: Bony Fish", "10%3A_Vertebrates/10.06%3A_Section_6-"),
            ("10.7: Amphibians", "10%3A_Vertebrates/10.07%3A_Amphibians"),
            ("10.8: Salamanders", "10%3A_Vertebrates/10.08%3A_Salamanders"),
            ("10.9: Frogs and Toads", "10%3A_Vertebrates/10.09%3A_Frogs_and_Toads"),
            ("10.10: Amphibian Evolution and Ecology", "10%3A_Vertebrates/10.10%3A_Amphibian_Evolution_and_Ecology"),
            ("10.11: Reptiles", "10%3A_Vertebrates/10.11%3A_Reptiles"),
            ("10.12: Lizards and Snakes", "10%3A_Vertebrates/10.12%3A_Lizards_and_Snakes"),
            ("10.13: Crocodilia", "10%3A_Vertebrates/10.13%3A_Crocodilia"),
            ("10.14: Turtles", "10%3A_Vertebrates/10.14%3A_Turtles"),
            ("10.15: Importance of Reptiles", "10%3A_Vertebrates/10.15%3A_Importance_of_Reptiles"),
            ("10.16: Birds", "10%3A_Vertebrates/10.16%3A_Birds"),
            ("10.17: Bird Reproduction", "10%3A_Vertebrates/10.17%3A_Bird_Reproduction"),
            ("10.18: Bird Diversity", "10%3A_Vertebrates/10.18%3A_Bird_Diversity"),
            ("10.19: Importance of Birds", "10%3A_Vertebrates/10.19%3A_Importance_of_Birds"),
            ("10.20: Mammal Overview", "10%3A_Vertebrates/10.20%3A_Mammal_Overview"),
            ("10.21: Mammal Reproduction", "10%3A_Vertebrates/10.21%3A_Mammal_Reproduction"),
            ("10.22: Mammal Classification", "10%3A_Vertebrates/10.22%3A_Mammal_Classification"),
            ("10.23: Importance of Mammals", "10%3A_Vertebrates/10.23%3A_Importance_of_Mammals"),
            ("10.24: Primates", "10%3A_Vertebrates/10.24%3A_Primates"),
            ("10.25: Primates and Humans", "10%3A_Vertebrates/10.25%3A_Primates_and_Humans"),
        ],
        "standards": [],
    },
    {
        "subject_slug": "science",
        "subject_name": "Science",
        "concept_slug": "human-body-systems",
        "concept_name": "Human Body Systems",
        "grade_band": "6",
        "source": "ck12-life-science-middle-school",
        "license": CK12_LICENSE,
        "title": "CK-12 Life Science for Middle School: Human Body Systems",
        "source_url": "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/11%3A_Human_Biology",
        "kind": "libretexts",
        "pages": [
            ("11.1: Human Body", "11%3A_Human_Biology/11.01%3A_Section_1-"),
            ("11.2: Homeostasis", "11%3A_Human_Biology/11.02%3A_Section_2-"),
            ("11.3: Skin", "11%3A_Human_Biology/11.03%3A_Section_3-"),
            ("11.4: Skin Health", "11%3A_Human_Biology/11.04%3A_Section_4-"),
            ("11.5: Nails and Hair", "11%3A_Human_Biology/11.05%3A_Section_5-"),
            ("11.6: Skeletal System", "11%3A_Human_Biology/11.06%3A_Section_6-"),
            ("11.7: Bone Health", "11%3A_Human_Biology/11.07%3A_Bone_Health"),
            ("11.8: Joints", "11%3A_Human_Biology/11.08%3A_Joints"),
            ("11.9: Muscles", "11%3A_Human_Biology/11.09%3A_Muscles"),
            ("11.10: Skeletal Muscles", "11%3A_Human_Biology/11.10%3A_Skeletal_Muscles"),
            ("11.11: Exercise", "11%3A_Human_Biology/11.11%3A_Exercise"),
            ("11.12: Food and Nutrients", "11%3A_Human_Biology/11.12%3A_Food_and_Nutrients"),
            ("11.13: Types of Nutrients", "11%3A_Human_Biology/11.13%3A_Types_of_Nutrients"),
            ("11.14: Vitamins and Minerals", "11%3A_Human_Biology/11.14%3A_Vitamins_and_Minerals"),
            ("11.15: Balanced Eating", "11%3A_Human_Biology/11.15%3A_Balanced_Eating"),
            ("11.16: Digestive System", "11%3A_Human_Biology/11.16%3A_Digestive_System"),
            ("11.17: Digestive System Organs", "11%3A_Human_Biology/11.17%3A_Digestive_System_Organs"),
            ("11.18: Digestive System Enzymes", "11%3A_Human_Biology/11.18%3A_Digestive_System_Enzymes"),
            ("11.19: Digestive System Bacteria", "11%3A_Human_Biology/11.19%3A_Digestive_System_Bacteria"),
            ("11.20: Digestive System Health", "11%3A_Human_Biology/11.20%3A_Digestive_System_Health"),
            ("11.21: Cardiovascular System", "11%3A_Human_Biology/11.21%3A_Cardiovascular_System"),
            ("11.22: Lymphatic System", "11%3A_Human_Biology/11.22%3A_Lymphatic_System"),
            ("11.23: Heart", "11%3A_Human_Biology/11.23%3A_Heart"),
            ("11.24: Blood Vessels", "11%3A_Human_Biology/11.24%3A_Blood_Vessels"),
            ("11.25: Blood Pressure", "11%3A_Human_Biology/11.25%3A_Blood_Pressure"),
            ("11.26: Blood", "11%3A_Human_Biology/11.26%3A_Blood"),
            ("11.27: Blood Type", "11%3A_Human_Biology/11.27%3A_Blood_Type"),
            ("11.28: Blood Diseases", "11%3A_Human_Biology/11.28%3A_Blood_Diseases"),
            ("11.29: Cardiovascular Diseases", "11%3A_Human_Biology/11.29%3A_Cardiovascular_Diseases"),
            ("11.30: Cardiovascular Health", "11%3A_Human_Biology/11.30%3A_Cardiovascular_Health"),
            ("11.31: Respiratory System", "11%3A_Human_Biology/11.31%3A_Respiratory_System"),
            ("11.33: Respiratory Systems Disorder", "11%3A_Human_Biology/11.33%3A_Respiratory_Systems_Disorder"),
            ("11.34: Respiratory System Health", "11%3A_Human_Biology/11.34%3A_Respiratory_System_Health"),
            ("11.35: Breathing", "11%3A_Human_Biology/11.35%3A_Breathing"),
            ("11.36: Excretory System", "11%3A_Human_Biology/11.36%3A_Excretory_System"),
            ("11.37: Urinary System", "11%3A_Human_Biology/11.37%3A_Urinary_System"),
            ("11.38: Kidneys", "11%3A_Human_Biology/11.38%3A_Kidneys"),
            ("11.39: Excretory System Diseases", "11%3A_Human_Biology/11.39%3A_Excretory_System_Diseases"),
            ("11.40: Nervous System", "11%3A_Human_Biology/11.40%3A_Nervous_System"),
            ("11.41: Nerve Impulse", "11%3A_Human_Biology/11.41%3A_Nerve_Impulse"),
            ("11.42: Central Nervous System", "11%3A_Human_Biology/11.42%3A_Central_Nervous_System"),
            ("11.43: Peripheral Nervous System", "11%3A_Human_Biology/11.43%3A_Peripheral_Nervous_System"),
            ("11.44: Nervous System Diseases", "11%3A_Human_Biology/11.44%3A_Nervous_System_Diseases"),
            ("11.45: Nervous System Injuries", "11%3A_Human_Biology/11.45%3A_Nervous_System_Injuries"),
            ("11.46: Nervous System Health", "11%3A_Human_Biology/11.46%3A_Nervous_System_Health"),
            ("11.47: Vision", "11%3A_Human_Biology/11.47%3A_Vision"),
            ("11.48: Eyes", "11%3A_Human_Biology/11.48%3A_Eyes"),
            ("11.49: Vision Correction", "11%3A_Human_Biology/11.49%3A_Vision_Correction"),
            ("11.50: Hearing and Balance", "11%3A_Human_Biology/11.50%3A_Hearing_and_Balance"),
            ("11.51: Touch", "11%3A_Human_Biology/11.51%3A_Touch"),
            ("11.52: Taste and Smell", "11%3A_Human_Biology/11.52%3A_Taste_and_Smell"),
            ("11.53: Pathogen", "11%3A_Human_Biology/11.53%3A_Pathogen"),
            ("11.54: HIV AIDS", "11%3A_Human_Biology/11.54%3A_HIV_AIDS"),
            ("11.55: Infectious Diseases", "11%3A_Human_Biology/11.55%3A_Infectious_Diseases"),
            ("11.56: Carcinogens and Cancer", "11%3A_Human_Biology/11.56%3A_Carcinogens_and_Cancer"),
            ("11.57: Diabetes", "11%3A_Human_Biology/11.57%3A_Diabetes"),
            ("11.58: Autoimmune Disease", "11%3A_Human_Biology/11.58%3A_Autoimmune_Disease"),
            ("11.59: Noninfectious Diseases", "11%3A_Human_Biology/11.59%3A_Noninfectious_Diseases"),
            ("11.60: Innate Immune System", "11%3A_Human_Biology/11.60%3A_Innate_Immune_System"),
            ("11.61: Inflammatory Response", "11%3A_Human_Biology/11.61%3A_Inflammatory_Response"),
            ("11.62: Humoral Response", "11%3A_Human_Biology/11.62%3A_Humoral_Response"),
            ("11.63: Immunity", "11%3A_Human_Biology/11.63%3A_Immunity"),
        ],
        "standards": [],
    },
]

LIBRETEXTS_BASE = "https://k12.libretexts.org/Bookshelves/Science_and_Technology/Life_Science_for_Middle_School_(CK-12)/"


_PDF_CACHE: dict[str, pypdf.PdfReader] = {}


def load_pdf_text(url: str, page_range: tuple[int, int]) -> str:
    """
    Extract text from a page range of a PDF at the given URL.

    Several resources in RESOURCES share the same module PDF (one entry
    per topic), so the reader is cached per URL for the life of the
    process -- otherwise a module referenced by N topics gets downloaded
    N times.
    """
    reader = _PDF_CACHE.get(url)
    if reader is None:
        response = httpx.get(url, timeout=60)
        response.raise_for_status()
        reader = pypdf.PdfReader(io.BytesIO(response.content))
        _PDF_CACHE[url] = reader
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
    # prepare_threshold=None: Supabase's transaction-mode pooler multiplexes
    # sessions onto shared server connections, so psycopg's autoprepare can
    # collide with another session's prepared statement (same fix as
    # app/db.py's pool).
    conn = psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None)
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
