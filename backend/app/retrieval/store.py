"""Vector similarity search against document_chunks, metadata-filtered first."""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.retrieval.models import RetrievedChunk


async def search_chunks(
    pool: AsyncConnectionPool,
    query_embedding: list[float],
    *,
    subject_slug: str,
    grade_band: str,
    concept_slug: str | None = None,
    limit: int = 8,
) -> list[RetrievedChunk]:
    """
    Return the top matching chunks for a subject and grade band, ranked
    by cosine similarity. Metadata filters narrow the candidate pool
    before similarity ranking runs, per architecture §15.
    """
    embedding_literal = str(query_embedding)
    filters = "s.slug = %(subject_slug)s and c.grade_band = %(grade_band)s"
    params: dict[str, object] = {
        "subject_slug": subject_slug,
        "grade_band": grade_band,
        "embedding": embedding_literal,
        "limit": limit,
    }
    if concept_slug is not None:
        filters += " and c.slug = %(concept_slug)s"
        params["concept_slug"] = concept_slug

    query = f"""
        select
            dc.id as chunk_id,
            cr.title as resource_title,
            cr.source_url as source_url,
            cr.license as license,
            dc.content as content,
            1 - (dc.embedding <=> %(embedding)s) as similarity,
            std.code as standard_code,
            fw.name as framework_name
        from document_chunks dc
        join curriculum_resources cr on cr.id = dc.resource_id
        join concepts c on c.id = cr.concept_id
        join subjects s on s.id = c.subject_id
        left join lateral (
            select st.code, st.framework_id
            from concept_standards cst
            join standards st on st.id = cst.standard_id
            where cst.concept_id = c.id
            order by st.code
            limit 1
        ) std on true
        left join curriculum_frameworks fw on fw.id = std.framework_id
        where {filters}
        order by dc.embedding <=> %(embedding)s
        limit %(limit)s
    """

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            rows = await cur.fetchall()

    return [
        RetrievedChunk(
            chunk_id=str(row["chunk_id"]),
            resource_title=row["resource_title"],
            source_url=row["source_url"] or "",
            license=row["license"],
            content=row["content"],
            similarity=float(row["similarity"]),
            standard_code=row["standard_code"],
            framework_name=row["framework_name"],
        )
        for row in rows
    ]
