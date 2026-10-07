"""
Golden set for the RAGAS-style evaluation harness (Decision 032).

Curated test fixture data, not user content -- versioned in git like
code, one case per real ingested concept (`concepts.slug`, confirmed
live against the actual database before writing these), plus a few
deliberately out-of-corpus probes that exercise the existing
low-confidence fallback (Decision 020/026) instead of the four RAGAS
scores, since there's no retrieved evidence to score those against.

Scoped to single-turn, direct-answer-eligible questions only: no
`GoldenCase` here carries conversation history, so every case runs
through the pipeline in its default "guiding" strategy with the
struggle/confirm counters at zero. Guided-discovery follow-up turns and
escalated strategies (explain, confirm_*) don't have one single "the
answer" to hold up against RAGAS's criteria -- they're a deliberate
scope limitation of this harness, not an oversight, and are called out
as such in the generated report.
"""

from typing import Literal

from pydantic import BaseModel


class GoldenCase(BaseModel):
    """One hand-curated question, with enough reference material to score all four RAGAS metrics against it."""

    id: str
    question: str
    subject_slug: Literal["math", "science"]
    concept_slug: str | None
    grade_band: str = "6"
    reference_facts: list[str] = []
    expect_fallback: bool = False


GOLDEN_SET: list[GoldenCase] = [
    GoldenCase(
        id="ratios-unit-rate",
        question="What is a unit rate?",
        subject_slug="math",
        concept_slug="ratios-and-unit-rates",
        reference_facts=[
            "A unit rate compares a quantity to exactly one unit of another quantity.",
            "A unit rate is found by dividing so the second term of the ratio becomes 1.",
        ],
    ),
    GoldenCase(
        id="fractions-dividing",
        question="How do you divide a fraction by another fraction?",
        subject_slug="math",
        concept_slug="arithmetic-operations-fractions-decimals",
        reference_facts=[
            "Dividing by a fraction is the same as multiplying by its reciprocal.",
            "The reciprocal of a fraction swaps its numerator and denominator.",
            "The result of dividing two numbers is called the quotient.",
        ],
    ),
    GoldenCase(
        id="expressions-variable",
        question="What is a variable in a math expression?",
        subject_slug="math",
        concept_slug="expressions-and-equations",
        reference_facts=[
            "A variable is a letter used to represent an unknown or changing number.",
            "A coefficient is the number that multiplies a variable in a term.",
        ],
    ),
    GoldenCase(
        id="rational-absolute-value",
        question="What does absolute value mean?",
        subject_slug="math",
        concept_slug="rational-numbers",
        reference_facts=[
            "Absolute value is the distance a number is from zero on the number line.",
            "Absolute value is always zero or positive, never negative.",
            "Opposite numbers are the same distance from zero but on different sides of it.",
        ],
    ),
    GoldenCase(
        id="surface-area-prism",
        question="How do you find the surface area of a rectangular prism?",
        subject_slug="math",
        concept_slug="area-surface-area-volume",
        reference_facts=[
            "Surface area is the sum of the areas of all the faces of a solid.",
            "A net is a 2-D unfolded version of a 3-D solid used to find its surface area.",
        ],
    ),
    GoldenCase(
        id="statistics-mad",
        question="What is mean absolute deviation and what does it tell you?",
        subject_slug="math",
        concept_slug="statistics",
        reference_facts=[
            "Mean absolute deviation measures the average distance of data points from the mean.",
            "A smaller mean absolute deviation means the data is more tightly clustered around the mean.",
            "Interquartile range is typically used to describe spread for a skewed distribution instead of MAD.",
        ],
    ),
    GoldenCase(
        id="cell-organelles",
        question="What are organelles and what do they do for a cell?",
        subject_slug="science",
        concept_slug="cell-structure-and-function",
        reference_facts=[
            "Organelles are specialized structures within a cell that each perform a specific function.",
            "The cell membrane controls what substances enter and exit the cell.",
        ],
    ),
    GoldenCase(
        id="genetics-dna-allele",
        question="What is DNA and what is an allele?",
        subject_slug="science",
        concept_slug="genetics-and-molecular-biology",
        reference_facts=[
            "DNA carries the genetic instructions for an organism's traits.",
            "An allele is a specific version of a gene.",
        ],
    ),
    GoldenCase(
        id="evolution-natural-selection",
        question="What is natural selection?",
        subject_slug="science",
        concept_slug="evolution-and-natural-selection",
        reference_facts=[
            (
                "Natural selection is the process by which organisms better suited to their environment "
                "survive and reproduce more successfully."
            ),
            "An adaptation is a trait that helps an organism survive in its environment.",
        ],
    ),
    GoldenCase(
        id="ecosystems-producer",
        question="What is a producer's role in a food web?",
        subject_slug="science",
        concept_slug="ecosystems-and-interactions",
        reference_facts=[
            "A producer is an organism that makes its own food, forming the base of a food web.",
            "A food web shows how energy flows between producers and the organisms that consume them.",
        ],
    ),
    GoldenCase(
        id="human-body-nervous-circulatory",
        question="What does the nervous system do, and how does it work with the circulatory system?",
        subject_slug="science",
        concept_slug="human-body-systems",
        reference_facts=[
            "The nervous system carries electrical signals through the body to control actions and senses.",
            "The circulatory system delivers oxygen and nutrients to the body's cells by pumping blood.",
        ],
    ),
    GoldenCase(
        id="plant-photosynthesis",
        question="How do plants make their own food?",
        subject_slug="science",
        concept_slug="plant-biology",
        reference_facts=[
            "Plants make their own food through a process called photosynthesis.",
            "Photosynthesis uses sunlight, water, and carbon dioxide to produce food for the plant.",
        ],
    ),
    GoldenCase(
        id="protists-fungi",
        question="What is a protist, and how can fungi reproduce?",
        subject_slug="science",
        concept_slug="protists-and-fungi",
        reference_facts=[
            (
                "A protist is a simple organism, often single-celled, that doesn't fit into the animal, "
                "plant, fungus, or bacteria groups."
            ),
            "Fungi can reproduce by releasing spores.",
        ],
    ),
    GoldenCase(
        id="virus-vs-bacteria",
        question="What's the difference between a virus and bacteria?",
        subject_slug="science",
        concept_slug="viruses-and-bacteria",
        reference_facts=[
            "Bacteria are single-celled organisms capable of reproducing on their own.",
            "A virus needs to infect a host cell in order to reproduce.",
        ],
    ),
    GoldenCase(
        id="vertebrate-backbone",
        question="What makes an animal a vertebrate, and what's an example group?",
        subject_slug="science",
        concept_slug="vertebrate-diversity",
        reference_facts=[
            "A vertebrate is an animal that has a backbone.",
            "Mammals are a major group within the vertebrates.",
        ],
    ),
    GoldenCase(
        id="invertebrate-no-backbone",
        question="What is an invertebrate, and what's an example group?",
        subject_slug="science",
        concept_slug="invertebrate-diversity",
        reference_facts=[
            "An invertebrate is an animal without a backbone.",
            "Arthropods are a large group of invertebrates.",
        ],
    ),
    GoldenCase(
        id="behavior-instinct-vs-learned",
        question="What's the difference between instinct and learned behavior in animals?",
        subject_slug="science",
        concept_slug="animal-behavior",
        reference_facts=[
            "Instinct is an inborn behavior an animal performs automatically without being taught.",
            "Learned behavior is developed through experience, not present from birth.",
        ],
    ),
    GoldenCase(
        id="hypothesis-scientific-method",
        question="What is a hypothesis and how does it fit into the scientific method?",
        subject_slug="science",
        concept_slug="introduction-to-life-science",
        reference_facts=[
            "A hypothesis is a testable explanation or educated guess made before testing it.",
            "The scientific method uses hypotheses to test ideas through observation and experimentation.",
        ],
    ),
    GoldenCase(
        id="fallback-pythagorean",
        question="What is the Pythagorean theorem and how do you use it?",
        subject_slug="math",
        concept_slug=None,
        expect_fallback=True,
    ),
    GoldenCase(
        id="fallback-slope",
        question="How do you find the slope of a line on a graph?",
        subject_slug="math",
        concept_slug=None,
        expect_fallback=True,
    ),
    GoldenCase(
        id="fallback-moon-phases",
        question="What causes the phases of the moon?",
        subject_slug="science",
        concept_slug=None,
        expect_fallback=True,
    ),
    GoldenCase(
        id="fallback-chemical-energy",
        question="How do chemical reactions release or absorb energy?",
        subject_slug="science",
        concept_slug=None,
        expect_fallback=True,
    ),
]
