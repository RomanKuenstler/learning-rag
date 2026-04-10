from __future__ import annotations

import logging
from pathlib import Path

from services.common.config import Settings
from services.embedder.chunking import Chunker
from services.embedder.embedding import EmbeddingClient
from services.embedder.postgres_client import EmbedderPostgresClient
from services.embedder.processors.processor_registry import ProcessorRegistry
from services.embedder.qdrant_client import EmbedderQdrantClient
from services.embedder.utils import compute_sha256, normalize_tags

LOGGER = logging.getLogger(__name__)


class FileProcessor:
    def __init__(
        self,
        *,
        data_dir: Path,
        chunker: Chunker,
        embedding_client: EmbeddingClient,
        postgres_client: EmbedderPostgresClient,
        qdrant_client: EmbedderQdrantClient,
        tags_map: dict[str, list[str]],
        settings: Settings,
    ) -> None:
        self.data_dir = data_dir
        self.chunker = chunker
        self.embedding_client = embedding_client
        self.postgres_client = postgres_client
        self.qdrant_client = qdrant_client
        self.tags_map = tags_map
        self.settings = settings
        self.registry = ProcessorRegistry(settings=settings, data_dir=data_dir)

    def process(self, file_path: Path) -> None:
        file_hash = compute_sha256(file_path)
        relative_path = str(file_path.relative_to(self.data_dir))
        resolved_tags = self.resolve_tags(relative_path, file_path.name)
        path_parts = Path(relative_path).parts
        existing_record = self.postgres_client.get_file(relative_path)
        uploaded_by_user_id = None
        is_system = len(path_parts) == 1
        is_global = is_system
        source_origin = "system_data" if is_system else "unknown"
        if len(path_parts) >= 3 and path_parts[0] == "uploads":
            owner = self.postgres_client.get_user_by_username(path_parts[1])
            uploaded_by_user_id = owner.id if owner is not None else None
            is_system = False
            if existing_record is not None and existing_record.source_origin in {"admin_upload", "user_upload"}:
                is_global = bool(existing_record.is_global)
                source_origin = existing_record.source_origin
            elif owner is not None and owner.role == "admin":
                is_global = True
                source_origin = "admin_upload"
            else:
                is_global = False
                source_origin = "user_upload"
        elif existing_record is not None and existing_record.source_origin:
            if existing_record.source_origin in {"system_data", "admin_upload", "user_upload"}:
                source_origin = existing_record.source_origin
                is_global = bool(existing_record.is_global)
        processor = self.registry.for_path(file_path)
        extraction = processor.process(file_path=file_path, relative_path=relative_path, tags=resolved_tags)
        chunk_payloads = self.chunker.split(extraction, relative_path) if extraction.text.strip() else []
        tagged_chunks = [{**chunk, "tags": resolved_tags} for chunk in chunk_payloads]
        embeddings = self.embedding_client.embed_documents([chunk["text"] for chunk in tagged_chunks]) if tagged_chunks else []
        LOGGER.info(
            "Processed extraction",
            extra={
                "file_path": relative_path,
                "processor": processor.processor_name,
                "extraction_method": extraction.metadata.get("extraction_method"),
                "ocr_used": extraction.processing_flags.get("ocr_used", False),
                "quality_flags": extraction.quality.flags,
                "semantic_blocks": len(extraction.semantic_blocks),
                "chunks": len(tagged_chunks),
            },
        )

        if tagged_chunks:
            self.qdrant_client.sync_file(
                file_name=file_path.name,
                file_path=relative_path,
                file_hash=file_hash,
                tags=resolved_tags,
                chunks=tagged_chunks,
                embeddings=embeddings,
            )
        else:
            self.qdrant_client.delete_file(relative_path)
        self.postgres_client.upsert_file_with_chunks(
            file_payload={
                "file_path": relative_path,
                "file_name": file_path.name,
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size,
                "chunk_count": len(tagged_chunks),
                "file_hash": file_hash,
                "content_hash": extraction.metadata.get("content_hash", ""),
                "file_type": extraction.metadata.get("extension", "").lstrip(".") or "unknown",
                "processing_status": extraction.processing_flags.get("processing_status", "processed"),
                "is_embedded": bool(tagged_chunks),
                "processing_error": extraction.processing_flags.get("processing_error"),
                "last_extraction_method": extraction.metadata.get("extraction_method"),
                "document_title": extraction.document_title,
                "author": extraction.metadata.get("author"),
                "detected_language": extraction.metadata.get("detected_language"),
                "index_schema_version": self.settings.index_schema_version,
                "processor_version": self.settings.processor_version,
                "normalization_version": self.settings.normalization_version,
                "extraction_strategy_version": self.settings.extraction_strategy_version,
                "chunk_size": self.settings.chunk_size,
                "chunk_overlap": self.settings.chunk_overlap,
                "processing_signature": self.settings.processing_signature,
                "extraction_quality": extraction.quality.to_metadata(),
                "processing_flags": extraction.processing_flags,
                "ocr_used": bool(extraction.processing_flags.get("ocr_used", False)),
                "tags": resolved_tags,
                "uploaded_by_user_id": uploaded_by_user_id,
                "is_system": is_system,
                "is_global": is_global,
                "source_origin": source_origin,
            },
            chunks=tagged_chunks,
        )
        LOGGER.info("Processed file", extra={"file_path": relative_path, "chunks": len(tagged_chunks)})

    def delete(self, relative_path: str) -> None:
        self.qdrant_client.delete_file(relative_path)
        self.postgres_client.delete_file(relative_path)
        LOGGER.info("Deleted file state", extra={"file_path": relative_path})

    def resolve_tags(self, relative_path: str, file_name: str) -> list[str]:
        tags = self.tags_map.get(relative_path, self.tags_map.get(file_name, []))
        return normalize_tags(tags, self.settings.default_tag)
