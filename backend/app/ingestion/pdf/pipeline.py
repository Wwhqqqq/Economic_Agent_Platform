from __future__ import annotations



import io

from dataclasses import dataclass, field



from app.ingestion.chunker import chunk_plain_text

from app.ingestion.ndm import NdmBlock, NormalizedDocument

from app.ingestion.pdf.classifier import classify_pdf_pages

from app.ingestion.pdf.extractor import extract_pdf_pages

from app.ingestion.pdf.financial_template import detect_financial_report, enrich_tables_with_sections

from app.ingestion.pdf.ocr_pipeline import ocr_pdf_pages

from app.ingestion.pdf.preprocessor import mark_header_footer_blocks, pages_to_plain_text

from app.ingestion.pdf.table_chunker import chunk_all_tables

from app.ingestion.pdf.table_extractor import extract_tables_from_pdf, extract_tables_from_text_blocks

from app.ingestion.pipeline_common import IngestPipelineResult, persist_ingest_artifacts

from app.rag.entity_extractor import build_document_title

from app.storage import doc_content_key, doc_source_key, get_storage



PARSER_VERSION = "pdf_pipeline_v2"





def _build_ndm_from_pages(

    pages,

    *,

    doc_id: str,

    user_id: int,

    filename: str | None,

    title: str,

    classification,

    tables=None,

) -> NormalizedDocument:

    blocks: list[NdmBlock] = []

    for page in pages:

        for block in page.blocks:

            if block.role != "body" or not block.text.strip():

                continue

            blocks.append(

                NdmBlock(

                    block_id=block.block_id,

                    type="paragraph",

                    text=block.text.strip(),

                    section_path=[f"Page {page.page_no}"],

                    page_no=page.page_no,

                    bbox=block.bbox,

                    role=block.role,

                )

            )

    for table in tables or []:

        blocks.append(

            NdmBlock(

                block_id=table.table_id,

                type="table",

                text=table.markdown[:2000],

                section_path=[table.section_path or f"Page {table.page_no}"],

                page_no=table.page_no,

                role="body",

            )

        )

    return NormalizedDocument(

        doc_id=doc_id,

        user_id=user_id,

        source_type="pdf",

        title=title,

        filename=filename,

        blocks=blocks,

        doc_metadata={"doc_class": classification.doc_class},

        parse_metadata={

            "parser_version": PARSER_VERSION,

            "doc_class": classification.doc_class,

            "confidence": classification.confidence,

            "signals": classification.signals,

            "table_count": len(tables or []),

        },

    )





def _extract_all_tables(pdf_bytes: bytes, pages, doc_class: str):

    tables = extract_tables_from_pdf(pdf_bytes)

    if not tables and doc_class in ("table_heavy", "native_text"):

        tables = extract_tables_from_text_blocks(pages)

    return tables





def _collect_pdf_figures(
    pdf_bytes: bytes,
    *,
    doc_id: str,
    user_id: int,
) -> tuple[list, list, list]:
    from app.ingestion.media.service import parse_image_bytes
    from app.ingestion.pdf.extractor import extract_pdf_figures

    chunks: list = []
    facts: list = []
    assets: list = []
    for fig in extract_pdf_figures(pdf_bytes):
        parsed = parse_image_bytes(
            fig.image_bytes,
            user_id,
            filename=f"{fig.figure_id}.png",
            doc_id=doc_id,
            source="pdf_extract",
            page_no=fig.page_no,
            bbox=fig.bbox,
            caption_hint=fig.caption_hint,
            index=True,
        )
        assets.append(parsed)
        if parsed.skip_index:
            continue
        chunks.extend(parsed.chunks)
        facts.extend(parsed.facts)
    return chunks, facts, assets


def _collect_facts(tables, *, doc_id: str, user_id: int, company: str | None = None):
    from app.rag.fact_store import FactRecord, get_fact_store

    store = get_fact_store()
    facts: list[FactRecord] = []
    for table in tables:
        facts.extend(store.extract_facts_from_table(table, doc_id=doc_id, user_id=user_id, company=company))
    return facts





def prepare_pdf_ingest(

    pdf_bytes: bytes,

    doc_id: str,

    user_id: int,

    *,

    filename: str | None = None,

    metadata: dict | None = None,

) -> IngestPipelineResult:

    storage = get_storage()

    ext = ".pdf"

    if filename and "." in filename:

        ext = "." + filename.rsplit(".", 1)[-1].lower()

    source_uri = storage.save_bytes(doc_source_key(user_id, doc_id, ext), pdf_bytes)



    pages = extract_pdf_pages(pdf_bytes)

    classification = classify_pdf_pages(pages)

    doc_class = classification.doc_class



    if doc_class == "scanned":

        ocr_result = ocr_pdf_pages(pdf_bytes)

        if ocr_result.avg_quality >= 0.75 and ocr_result.plain_text.strip():

            pages = ocr_result.pages

            pages = mark_header_footer_blocks(pages)

            plain_text = ocr_result.plain_text

            title = build_document_title(plain_text[:500] or filename or doc_id, doc_id)

            tables = _extract_all_tables(pdf_bytes, pages, "scanned")

            enrich_tables_with_sections(tables, plain_text)

            table_chunks = chunk_all_tables(tables, doc_id)

            text_chunks = chunk_plain_text(plain_text, doc_id)

            chunks = text_chunks + table_chunks

            facts = _collect_facts(tables, doc_id=doc_id, user_id=user_id)
            fig_chunks, fig_facts, fig_assets = _collect_pdf_figures(pdf_bytes, doc_id=doc_id, user_id=user_id)
            chunks = chunks + fig_chunks
            facts = facts + fig_facts

            ndm = _build_ndm_from_pages(

                pages, doc_id=doc_id, user_id=user_id, filename=filename,

                title=title, classification=classification, tables=tables,

            )

            if metadata:

                ndm.doc_metadata.update(metadata)

            storage.save_text(doc_content_key(user_id, doc_id), plain_text)

            result = IngestPipelineResult(

                doc_id=doc_id, title=title, ndm=ndm, chunks=chunks,

                ndm_uri="", content_uri=source_uri, parser_version=PARSER_VERSION,

                parse_status="ready", page_count=ocr_result.page_count,

                quality_score=ocr_result.avg_quality, plain_text=plain_text,

                tables=tables, facts=facts, doc_class="scanned_ocr",

                table_count=len(tables), figure_assets=fig_assets,

            )

            persist_ingest_artifacts(result, user_id, plain_text=plain_text)

            return result



        title = filename or f"PDF {doc_id[:8]}"

        ndm = NormalizedDocument(

            doc_id=doc_id, user_id=user_id, source_type="pdf", title=title, filename=filename,

            parse_metadata={"parser_version": PARSER_VERSION, "doc_class": "scanned", "signals": classification.signals},

        )

        if metadata:

            ndm.doc_metadata.update(metadata)

        result = IngestPipelineResult(

            doc_id=doc_id, title=title, ndm=ndm, chunks=[], ndm_uri="", content_uri=source_uri,

            parser_version=PARSER_VERSION, parse_status="needs_review",

            page_count=classification.page_count, quality_score=ocr_result.avg_quality,

            plain_text="", doc_class="scanned",

            error_message="扫描件 OCR 质量不足（<0.75），请人工审核或更换清晰扫描件",

        )

        persist_ingest_artifacts(result, user_id, plain_text="")

        return result



    pages = mark_header_footer_blocks(pages)

    plain_text = pages_to_plain_text(pages)

    body_sample = " ".join(

        b.text.strip() for p in pages for b in p.blocks if b.role == "body" and b.text.strip()

    )

    title = build_document_title(body_sample or filename or doc_id, doc_id)



    if detect_financial_report(body_sample or plain_text):

        doc_class = "financial_report"



    tables = _extract_all_tables(pdf_bytes, pages, doc_class)

    enrich_tables_with_sections(tables, plain_text)

    table_chunks = chunk_all_tables(tables, doc_id)

    text_chunks = chunk_plain_text(plain_text, doc_id)

    for chunk in text_chunks:

        for page in pages:

            if f"[Page {page.page_no}]" in chunk.text:

                chunk.page_range = str(page.page_no)

                break

    chunks = text_chunks + table_chunks

    facts = _collect_facts(tables, doc_id=doc_id, user_id=user_id)
    fig_chunks, fig_facts, fig_assets = _collect_pdf_figures(pdf_bytes, doc_id=doc_id, user_id=user_id)
    chunks = chunks + fig_chunks
    facts = facts + fig_facts

    ndm = _build_ndm_from_pages(

        pages, doc_id=doc_id, user_id=user_id, filename=filename,

        title=title, classification=classification, tables=tables,

    )

    ndm.doc_metadata["doc_class"] = doc_class

    if metadata:

        ndm.doc_metadata.update(metadata)



    storage.save_text(doc_content_key(user_id, doc_id), plain_text)

    result = IngestPipelineResult(

        doc_id=doc_id, title=title, ndm=ndm, chunks=chunks,

        ndm_uri="", content_uri=source_uri, parser_version=PARSER_VERSION,

        parse_status="ready", page_count=classification.page_count,

        quality_score=min(1.0, classification.avg_chars_per_page / 1500),

        plain_text=plain_text, tables=tables, facts=facts,

        doc_class=doc_class, table_count=len(tables), figure_assets=fig_assets,

    )

    persist_ingest_artifacts(result, user_id, plain_text=plain_text)

    return result


