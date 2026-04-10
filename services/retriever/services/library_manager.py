from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from services.common.config import Settings
from services.common.models import UserAccount
from services.embedder.processor import FileProcessor
from services.embedder.utils import load_tags, normalize_tags, save_tags
from services.retriever.schemas.chat import LibraryListResponse, LibrarySummaryRead
from services.retriever.services.message_mapper import map_library_file

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class UploadFilePayload:
    file_name: str
    content: bytes


class LibraryManager:
    def __init__(self, *, data_dir: Path, processor: FileProcessor, settings: Settings) -> None:
        self.data_dir = data_dir
        self.processor = processor
        self.settings = settings
        self.tags_path = data_dir / "tags.json"
        self.uploads_dir = data_dir / "uploads"

    def list_files(self, user: UserAccount, *, include_other_users: bool = False) -> LibraryListResponse:
        records = self.processor.postgres_client.list_files_for_user(
            user_id=user.id,
            is_admin=user.role == "admin",
            include_other_users=include_other_users,
        )
        users_by_id = {account.id: account for account in self.processor.postgres_client.list_users()}
        tags_map = load_tags(self.tags_path)
        normalized_records = []
        for record in records:
            if not record.extension:
                record.extension = Path(record.file_name).suffix.lower()
            absolute_path = self.data_dir / record.file_path
            if record.size_bytes <= 0 and absolute_path.exists():
                record.size_bytes = absolute_path.stat().st_size
            if not record.tags:
                record.tags = normalize_tags(tags_map.get(record.file_path, tags_map.get(record.file_name, [])), self.settings.default_tag)
            if record.chunk_count > 0 and not record.is_embedded:
                record.is_embedded = True
            normalized_records.append(record)
        summary = LibrarySummaryRead(
            total_files=len(normalized_records),
            embedded_files=sum(1 for record in normalized_records if record.is_embedded),
            total_chunks=sum(int(record.chunk_count or 0) for record in normalized_records),
        )
        return LibraryListResponse(
            files=[
                self._map_for_user(record, user=user, users_by_id=users_by_id)
                for record in normalized_records
            ],
            summary=summary,
            allowed_extensions=sorted(self.settings.allowed_upload_extension_set),
            max_upload_files=self.settings.max_upload_files,
            upload_max_file_size_mb=self.settings.upload_max_file_size_mb,
            default_tag=self.settings.default_tag,
        )

    def update_file_state(self, user: UserAccount, file_id: int, *, is_enabled: bool):
        record = self.processor.postgres_client.set_file_enabled_for_user(
            user_id=user.id,
            file_id=file_id,
            is_enabled=is_enabled,
            is_admin=user.role == "admin",
        )
        if record is None:
            return None
        users_by_id = {account.id: account for account in self.processor.postgres_client.list_users()}
        return self._map_for_user(record, user=user, users_by_id=users_by_id)

    def delete_file(self, user: UserAccount, file_id: int):
        record = self.processor.postgres_client.get_file_by_id(file_id)
        if record is None:
            return None
        if user.role != "admin":
            if record.is_global:
                raise PermissionError("Global files cannot be deleted by non-admin users")
            if record.uploaded_by_user_id != user.id:
                raise PermissionError("Users can only delete files they uploaded")

        absolute_path = self.data_dir / record.file_path
        if absolute_path.exists():
            absolute_path.unlink()

        self.processor.delete(record.file_path)
        self._remove_tags(record.file_path, record.file_name)
        users_by_id = {account.id: account for account in self.processor.postgres_client.list_users()}
        return self._map_for_user(record, user=user, users_by_id=users_by_id)

    def upload_files(self, user: UserAccount, uploads: list[UploadFilePayload], tags_by_file: dict[str, list[str]]):
        if len(uploads) > self.settings.max_upload_files:
            raise ValueError(f"Upload supports up to {self.settings.max_upload_files} files at a time")

        seen_names: set[str] = set()
        stored_records = []
        current_tags = load_tags(self.tags_path)
        users_by_id = {account.id: account for account in self.processor.postgres_client.list_users()}
        existing_names = {record.file_name for record in self.processor.postgres_client.list_files()}
        user_dir = self.uploads_dir / user.username
        user_dir.mkdir(parents=True, exist_ok=True)

        for upload in uploads:
            file_name = Path(upload.file_name).name
            if file_name != upload.file_name:
                raise ValueError(f"Invalid file name: {upload.file_name}")
            if file_name in seen_names:
                raise ValueError(f"Duplicate file in upload request: {file_name}")
            seen_names.add(file_name)
            if file_name in existing_names:
                raise ValueError(f"File already exists in library: {file_name}")

            suffix = Path(file_name).suffix.lower()
            if suffix not in self.settings.allowed_upload_extension_set:
                raise ValueError(f"Unsupported file type for {file_name}")

            max_bytes = self.settings.upload_max_file_size_mb * 1024 * 1024
            if len(upload.content) > max_bytes:
                raise ValueError(f"File exceeds {self.settings.upload_max_file_size_mb} MB limit: {file_name}")

        for upload in uploads:
            file_name = Path(upload.file_name).name
            target_path = user_dir / file_name
            target_path.write_bytes(upload.content)
            relative_path = str(target_path.relative_to(self.data_dir))
            normalized_tags = normalize_tags(tags_by_file.get(file_name, []), self.settings.default_tag)
            current_tags[relative_path] = normalized_tags
            current_tags[file_name] = normalized_tags
            save_tags(self.tags_path, current_tags)
            self.processor.tags_map = current_tags
            self.processor.process(target_path)
            record = self.processor.postgres_client.get_file(relative_path)
            if record is not None:
                stored_records.append(self._map_for_user(record, user=user, users_by_id=users_by_id))

        return stored_records

    def parse_tags_mapping(self, raw_value: str | None) -> dict[str, list[str]]:
        if not raw_value:
            return {}
        parsed = json.loads(raw_value)
        if not isinstance(parsed, dict):
            raise ValueError("tags_by_file must be a JSON object")

        tags_by_file: dict[str, list[str]] = {}
        for key, value in parsed.items():
            if isinstance(value, str):
                source_tags = value.split(",")
            elif isinstance(value, list):
                source_tags = [str(item) for item in value]
            else:
                raise ValueError(f"Invalid tags for {key}")
            tags_by_file[str(Path(str(key)).name)] = normalize_tags(source_tags, self.settings.default_tag)
        return tags_by_file

    def _remove_tags(self, relative_path: str, file_name: str) -> None:
        tags_map = load_tags(self.tags_path)
        removed = False
        for key in (relative_path, file_name):
            if key in tags_map:
                tags_map.pop(key, None)
                removed = True
        if removed:
            save_tags(self.tags_path, tags_map)
        self.processor.tags_map = tags_map

    def _map_for_user(self, record, *, user: UserAccount, users_by_id: dict[int, UserAccount]):
        owner = users_by_id.get(record.uploaded_by_user_id or -1)
        is_owned_by_current_user = record.uploaded_by_user_id == user.id
        can_delete = user.role == "admin" or (not record.is_global and is_owned_by_current_user)
        can_toggle_enabled = user.role == "admin" or not record.is_global
        return map_library_file(
            record,
            can_delete=can_delete,
            can_toggle_enabled=can_toggle_enabled,
            owner_user_id=record.uploaded_by_user_id,
            owner_username=owner.username if owner else None,
            owner_displayname=owner.displayname if owner else None,
            is_global=record.is_global,
            source_origin=record.source_origin,
            is_owned_by_current_user=is_owned_by_current_user,
        )
