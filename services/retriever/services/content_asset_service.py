from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlparse
from urllib.request import urlopen

from minio import Minio
from minio.error import S3Error

from services.common.config import Settings
from services.common.models import ContentAsset, LearningPath, UserAccount
from services.retriever.repositories.chat_repository import ChatRepository


def _safe_name(file_name: str) -> str:
    raw = os.path.basename(file_name or "asset.bin")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-.")
    return cleaned or "asset.bin"


def _extension(file_name: str) -> str:
    suffix = os.path.splitext(file_name)[1].lower()
    return suffix if suffix.startswith(".") else ""


def _mime_type(file_name: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or fallback


@dataclass(slots=True)
class AssetUploadResult:
    asset: ContentAsset
    presigned_url: str


class ContentAssetService:
    def __init__(self, repository: ChatRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self.enabled = bool(settings.minio_enabled)
        self._client: Minio | None = None
        if self.enabled:
            endpoint = settings.minio_endpoint
            parsed = urlparse(endpoint)
            endpoint_host = parsed.netloc or parsed.path
            secure = settings.minio_secure or parsed.scheme == "https"
            self._client = Minio(
                endpoint_host,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=secure,
                region=settings.minio_region or None,
            )
            self._ensure_bucket(settings.minio_content_bucket)
            self._ensure_bucket(settings.minio_submission_bucket)

    def _ensure_bucket(self, bucket_name: str) -> None:
        if not self._client or not bucket_name:
            return
        found = self._client.bucket_exists(bucket_name)
        if not found:
            self._client.make_bucket(bucket_name)

    def _bucket_for_source(self, source_type: str) -> str:
        if source_type in {"learner_submission_artifact", "runtime_submission_artifact"}:
            return self.settings.minio_submission_bucket
        return self.settings.minio_content_bucket

    def presigned_url(self, asset: ContentAsset) -> str:
        if not self._client:
            return ""
        try:
            return self._client.presigned_get_object(
                asset.bucket_name,
                asset.storage_key,
                expires=timedelta(seconds=max(60, int(self.settings.minio_url_expiry_seconds))),
            )
        except S3Error:
            return ""

    def upload_bytes(
        self,
        *,
        content: bytes,
        file_name: str,
        asset_kind: str,
        source_type: str,
        scope_type: str,
        owner_user_id: int | None = None,
        learning_path_id: str | None = None,
        node_id: str | None = None,
        chapter_id: str | None = None,
        branch_id: str | None = None,
        uploaded_by_user_id: int | None = None,
        attempt_id: str | None = None,
        download_label: str | None = None,
        caption: str | None = None,
        description: str | None = None,
        alt_text: str | None = None,
        file_category: str | None = None,
        metadata: dict[str, object] | None = None,
        mime_type: str | None = None,
        asset_status: str = "ready",
        media_kind: str | None = None,
        duration_seconds: float | None = None,
        is_optional: bool = True,
        is_required: bool = False,
        reuse_existing: bool = True,
    ) -> AssetUploadResult:
        normalized_name = _safe_name(file_name)
        ext = _extension(normalized_name)
        checksum = hashlib.sha256(content).hexdigest()
        bucket = self._bucket_for_source(source_type=source_type)
        guessed_mime = mime_type or _mime_type(normalized_name)

        if reuse_existing and learning_path_id and node_id:
            existing_candidates = self.repository.list_content_assets(
                learning_path_id=learning_path_id,
                node_id=node_id,
                source_type=source_type,
                asset_kinds=[asset_kind],
                limit=200,
            )
            for candidate in existing_candidates:
                if candidate.checksum_sha256 == checksum and candidate.normalized_filename == normalized_name:
                    return AssetUploadResult(asset=candidate, presigned_url=self.presigned_url(candidate))

        asset_id = str(uuid.uuid4())
        if source_type in {"learner_submission_artifact", "runtime_submission_artifact"}:
            storage_prefix = f"runtime/{owner_user_id or uploaded_by_user_id or 'user'}/{attempt_id or asset_id}"
        elif source_type == "course_attachment":
            storage_prefix = f"courses/{learning_path_id or 'course'}/attachments/{asset_id}"
        else:
            storage_prefix = f"courses/{learning_path_id or 'course'}/nodes/{node_id or 'node'}/assets/{asset_id}"
        storage_key = f"{storage_prefix}/{normalized_name}"

        if self._client:
            payload = BytesIO(content)
            self._client.put_object(
                bucket,
                storage_key,
                payload,
                length=len(content),
                content_type=guessed_mime,
            )

        asset = self.repository.create_content_asset(
            {
                "id": asset_id,
                "asset_kind": asset_kind,
                "media_kind": media_kind or asset_kind,
                "bucket_name": bucket,
                "storage_key": storage_key,
                "mime_type": guessed_mime,
                "original_filename": file_name,
                "normalized_filename": normalized_name,
                "file_extension": ext,
                "size_bytes": len(content),
                "checksum_sha256": checksum,
                "source_type": source_type,
                "scope_type": scope_type,
                "owner_user_id": owner_user_id,
                "learning_path_id": learning_path_id,
                "node_id": node_id,
                "chapter_id": chapter_id,
                "branch_id": branch_id,
                "uploaded_by_user_id": uploaded_by_user_id,
                "attempt_id": attempt_id,
                "asset_status": asset_status,
                "alt_text": alt_text or "",
                "caption": caption or "",
                "description": description or "",
                "download_label": download_label or "",
                "file_category": file_category or "",
                "is_optional": bool(is_optional),
                "is_required": bool(is_required),
                "duration_seconds": duration_seconds,
                "metadata_json": metadata or {},
            }
        )
        return AssetUploadResult(asset=asset, presigned_url=self.presigned_url(asset))

    def upload_from_url(
        self,
        *,
        source_url: str,
        file_name: str,
        asset_kind: str,
        source_type: str,
        scope_type: str,
        owner_user_id: int | None = None,
        learning_path_id: str | None = None,
        node_id: str | None = None,
        chapter_id: str | None = None,
        branch_id: str | None = None,
        uploaded_by_user_id: int | None = None,
        attempt_id: str | None = None,
        download_label: str | None = None,
        caption: str | None = None,
        description: str | None = None,
        alt_text: str | None = None,
        file_category: str | None = None,
        metadata: dict[str, object] | None = None,
        mime_type: str | None = None,
        asset_status: str = "ready",
        media_kind: str | None = None,
        duration_seconds: float | None = None,
        is_optional: bool = True,
        is_required: bool = False,
        reuse_existing: bool = True,
    ) -> AssetUploadResult:
        with urlopen(source_url, timeout=20) as response:  # nosec B310 - trusted curated runtime source
            body = response.read()
            guessed = response.headers.get_content_type()
        return self.upload_bytes(
            content=body,
            file_name=file_name,
            asset_kind=asset_kind,
            source_type=source_type,
            scope_type=scope_type,
            owner_user_id=owner_user_id,
            learning_path_id=learning_path_id,
            node_id=node_id,
            chapter_id=chapter_id,
            branch_id=branch_id,
            uploaded_by_user_id=uploaded_by_user_id,
            attempt_id=attempt_id,
            download_label=download_label,
            caption=caption,
            description=description,
            alt_text=alt_text,
            file_category=file_category,
            metadata=metadata,
            mime_type=mime_type or guessed,
            asset_status=asset_status,
            media_kind=media_kind,
            duration_seconds=duration_seconds,
            is_optional=is_optional,
            is_required=is_required,
            reuse_existing=reuse_existing,
        )

    def resolve_asset_catalog(self, asset_ids: list[str]) -> dict[str, dict[str, object]]:
        if not asset_ids:
            return {}
        records = self.repository.list_content_assets_by_ids(asset_ids=asset_ids)
        by_id: dict[str, dict[str, object]] = {}
        for record in records:
            by_id[record.id] = {
                "asset_id": record.id,
                "asset_kind": record.asset_kind,
                "media_kind": record.media_kind,
                "mime_type": record.mime_type,
                "file_name": record.normalized_filename or record.original_filename,
                "download_label": record.download_label or record.normalized_filename or record.original_filename,
                "size_bytes": int(record.size_bytes or 0),
                "caption": record.caption or "",
                "description": record.description or "",
                "alt_text": record.alt_text or "",
                "duration_seconds": record.duration_seconds,
                "url": self.presigned_url(record),
                "bucket_name": record.bucket_name,
                "storage_key": record.storage_key,
            }
        return by_id

    def can_read_asset(self, *, user: UserAccount, learning_path: LearningPath | None, asset: ContentAsset) -> bool:
        if user.role == "admin":
            return True
        if asset.source_type in {"learner_submission_artifact", "runtime_submission_artifact"}:
            return asset.owner_user_id == user.id or asset.uploaded_by_user_id == user.id
        if learning_path is None:
            return False
        if learning_path.scope == "global":
            return True
        return learning_path.owner_user_id == user.id
