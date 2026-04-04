from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from services.common.config import get_settings
from services.retriever.api.dependencies import get_app_auth_context, get_auth_context, get_retriever_service
from services.retriever.auth import AuthContext
from services.retriever.schemas.auth import (
    AdminUserCreateRequest,
    AdminUserRead,
    AdminUserUpdateRequest,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
)
from services.retriever.schemas.chat import (
    ChatDownloadResponse,
    ChatRead,
    ChatUpdateRequest,
    ErrorResponse,
    FilterFileListResponse,
    FilterFileRead,
    FilterTagListResponse,
    FilterTagRead,
    FilterUpdateRequest,
    GptChatRead,
    GptCreateRequest,
    GptDeleteResponse,
    GptPreviewMessageCreateRequest,
    GptRead,
    GptUpdateRequest,
    HealthResponse,
    LibraryFileRead,
    LibraryFileUpdateRequest,
    LibraryListResponse,
    LibraryUploadResponse,
    MessageCreateRequest,
    MessageCreateResponse,
    MessageRead,
    PersonalizationRead,
    PersonalizationUpdateRequest,
    SettingsRead,
    SettingsUpdateRequest,
)
from services.retriever.services.library_manager import UploadFilePayload
from services.retriever.services.retriever_service import RetrieverAppService


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Local RAG Retriever API", version="12.0.0")

    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Auth-Token", "X-Auth-Expires-At", "X-Auth-Max-Expires-At"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/api/auth/login", response_model=AuthLoginResponse, responses={401: {"model": ErrorResponse}})
    def login(
        payload: AuthLoginRequest,
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> AuthLoginResponse:
        try:
            return service.login(payload.username, payload.password)
        except PermissionError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    @app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        auth: AuthContext = Depends(get_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> Response:
        service.logout(auth)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/auth/me", response_model=AuthMeResponse)
    def me(
        auth: AuthContext = Depends(get_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> AuthMeResponse:
        return service.me(auth)

    @app.post("/api/auth/change-password", response_model=PasswordChangeResponse, responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    def change_password(
        payload: PasswordChangeRequest,
        auth: AuthContext = Depends(get_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> PasswordChangeResponse:
        try:
            return service.change_password(
                auth,
                current_password=payload.current_password,
                new_password=payload.new_password,
                confirm_password=payload.confirm_password,
            )
        except PermissionError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/admin/users", response_model=list[AdminUserRead], responses={403: {"model": ErrorResponse}})
    def list_admin_users(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[AdminUserRead]:
        try:
            return service.list_admin_users(auth)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.post("/api/admin/users", response_model=AdminUserRead, responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    def create_admin_user(
        payload: AdminUserCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> AdminUserRead:
        try:
            return service.create_admin_user(auth, username=payload.username, displayname=payload.displayname, role=payload.role)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.patch("/api/admin/users/{user_id}", response_model=AdminUserRead, responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    def update_admin_user(
        user_id: int,
        payload: AdminUserUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> AdminUserRead:
        try:
            user = service.update_admin_user(auth, user_id, **payload.model_dump(exclude_unset=True))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @app.delete("/api/admin/users/{user_id}", response_model=AdminUserRead, responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    def delete_admin_user(
        user_id: int,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> AdminUserRead:
        try:
            user = service.delete_admin_user(auth, user_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @app.post("/api/chats", response_model=ChatRead)
    def create_chat(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        return service.create_chat(auth.user)

    @app.get("/api/chats", response_model=list[ChatRead])
    def list_chats(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[ChatRead]:
        return service.list_chats(auth.user)

    @app.get("/api/chats/archived", response_model=list[ChatRead])
    def list_archived_chats(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[ChatRead]:
        return service.list_archived_chats(auth.user)

    @app.get("/api/chats/{chat_id}", response_model=ChatRead, responses={404: {"model": ErrorResponse}})
    def get_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        chat = service.get_chat(auth.user, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.patch("/api/chats/{chat_id}", response_model=ChatRead, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    def rename_chat(
        chat_id: str,
        payload: ChatUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            chat = service.rename_chat(auth.user, chat_id, payload.chat_name)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.patch("/api/chats/{chat_id}/archive", response_model=ChatRead, responses={404: {"model": ErrorResponse}})
    def archive_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        chat = service.archive_chat(auth.user, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.patch("/api/chats/{chat_id}/unarchive", response_model=ChatRead, responses={404: {"model": ErrorResponse}})
    def unarchive_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        chat = service.unarchive_chat(auth.user, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.delete("/api/chats/{chat_id}", response_model=ChatRead, responses={404: {"model": ErrorResponse}})
    def delete_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        chat = service.delete_chat(auth.user, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.get("/api/gpts", response_model=list[GptRead])
    def list_gpts(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[GptRead]:
        return service.list_gpts(auth.user)

    @app.post("/api/gpts", response_model=GptRead, responses={422: {"model": ErrorResponse}})
    def create_gpt(
        payload: GptCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptRead:
        try:
            return service.create_gpt(auth.user, payload)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/gpts/{gpt_id}", response_model=GptRead, responses={404: {"model": ErrorResponse}})
    def get_gpt(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptRead:
        record = service.get_gpt(auth.user, gpt_id)
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.patch("/api/gpts/{gpt_id}", response_model=GptRead, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    def update_gpt(
        gpt_id: str,
        payload: GptUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptRead:
        try:
            record = service.update_gpt(auth.user, gpt_id, payload)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.delete("/api/gpts/{gpt_id}", response_model=GptDeleteResponse, responses={404: {"model": ErrorResponse}})
    def delete_gpt(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptDeleteResponse:
        record = service.delete_gpt(auth.user, gpt_id)
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.post("/api/gpts/preview/messages", response_model=MessageCreateResponse, responses={422: {"model": ErrorResponse}})
    def preview_gpt_message(
        payload: GptPreviewMessageCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> MessageCreateResponse:
        try:
            return MessageCreateResponse(**service.preview_gpt_message(auth.user, payload))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/gpts/{gpt_id}/chat", response_model=GptChatRead, responses={404: {"model": ErrorResponse}})
    def get_gpt_chat(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptChatRead:
        record = service.get_gpt_chat(auth.user, gpt_id)
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.delete("/api/gpts/{gpt_id}/chat", response_model=GptChatRead, responses={404: {"model": ErrorResponse}})
    def clear_gpt_chat(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptChatRead:
        record = service.clear_gpt_chat(auth.user, gpt_id)
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.post("/api/gpts/{gpt_id}/messages", response_model=MessageCreateResponse, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
    async def create_gpt_message(
        gpt_id: str,
        request: Request,
        message: str | None = Form(default=None),
        files: list[UploadFile] | None = File(default=None),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> MessageCreateResponse:
        content_type = request.headers.get("content-type", "")
        payload_message = message
        attachments = files or []
        if "application/json" in content_type:
            payload = MessageCreateRequest(**(await request.json()))
            payload_message = payload.message

        if not payload_message or not payload_message.strip():
            raise HTTPException(status_code=422, detail="Message cannot be empty")

        try:
            uploads = [(upload.filename or "attachment.bin", await upload.read()) for upload in attachments]
            result = service.send_gpt_message(auth.user, gpt_id, payload_message.strip(), attachments=uploads)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Failed to generate assistant response: {error}") from error
        if result is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return MessageCreateResponse(**result)

    @app.get("/api/gpts/{gpt_id}/download", response_model=ChatDownloadResponse, responses={404: {"model": ErrorResponse}})
    def download_gpt_chat(
        gpt_id: str,
        response: Response,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatDownloadResponse:
        payload = service.download_gpt_chat(auth.user, gpt_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        safe_name = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in payload.chat_name)
        response.headers["Content-Disposition"] = f'attachment; filename="{safe_name or "gpt"}-{gpt_id}.json"'
        return payload

    @app.get("/api/chats/{chat_id}/messages", response_model=list[MessageRead], responses={404: {"model": ErrorResponse}})
    def get_messages(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[MessageRead]:
        chat = service.get_chat(auth.user, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return service.get_chat_messages(auth.user, chat_id)

    @app.get("/api/user/files", response_model=FilterFileListResponse)
    def list_user_files(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterFileListResponse:
        return FilterFileListResponse(**service.list_user_file_filters(auth.user))

    @app.patch("/api/user/files/{file_id}", response_model=FilterFileRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def update_user_file(
        file_id: int,
        payload: FilterUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterFileRead:
        try:
            record = service.update_user_file_filter(auth.user, file_id, is_enabled=payload.is_enabled)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="File not found")
        return record

    @app.get("/api/chats/{chat_id}/files", response_model=FilterFileListResponse, responses={404: {"model": ErrorResponse}})
    def list_chat_files(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterFileListResponse:
        records = service.list_chat_file_filters(auth.user, chat_id)
        if records is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return FilterFileListResponse(**records)

    @app.patch("/api/chats/{chat_id}/files/{file_id}", response_model=FilterFileRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def update_chat_file(
        chat_id: str,
        file_id: int,
        payload: FilterUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterFileRead:
        try:
            record = service.update_chat_file_filter(auth.user, chat_id, file_id, is_enabled=payload.is_enabled)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Chat or file not found")
        return record

    @app.get("/api/user/tags", response_model=FilterTagListResponse)
    def list_user_tags(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterTagListResponse:
        return FilterTagListResponse(**service.list_user_tag_filters(auth.user))

    @app.patch("/api/user/tags/{tag}", response_model=FilterTagRead, responses={404: {"model": ErrorResponse}})
    def update_user_tag(
        tag: str,
        payload: FilterUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterTagRead:
        record = service.update_user_tag_filter(auth.user, tag, is_enabled=payload.is_enabled)
        if record is None:
            raise HTTPException(status_code=404, detail="Tag not found")
        return record

    @app.get("/api/chats/{chat_id}/tags", response_model=FilterTagListResponse, responses={404: {"model": ErrorResponse}})
    def list_chat_tags(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterTagListResponse:
        records = service.list_chat_tag_filters(auth.user, chat_id)
        if records is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return FilterTagListResponse(**records)

    @app.patch("/api/chats/{chat_id}/tags/{tag}", response_model=FilterTagRead, responses={404: {"model": ErrorResponse}})
    def update_chat_tag(
        chat_id: str,
        tag: str,
        payload: FilterUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> FilterTagRead:
        record = service.update_chat_tag_filter(auth.user, chat_id, tag, is_enabled=payload.is_enabled)
        if record is None:
            raise HTTPException(status_code=404, detail="Chat or tag not found")
        return record

    @app.post(
        "/api/chats/{chat_id}/messages",
        response_model=MessageCreateResponse,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def create_message(
        chat_id: str,
        request: Request,
        message: str | None = Form(default=None),
        assistant_mode: str | None = Form(default=None),
        files: list[UploadFile] | None = File(default=None),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> MessageCreateResponse:
        content_type = request.headers.get("content-type", "")
        payload_message = message
        payload_assistant_mode = assistant_mode
        attachments = files or []
        if "application/json" in content_type:
            payload = MessageCreateRequest(**(await request.json()))
            payload_message = payload.message
            payload_assistant_mode = payload.assistant_mode

        if not payload_message or not payload_message.strip():
            raise HTTPException(status_code=422, detail="Message cannot be empty")

        try:
            uploads = [(upload.filename or "attachment.bin", await upload.read()) for upload in attachments]
            result = service.send_message(auth.user, chat_id, payload_message.strip(), uploads, assistant_mode=payload_assistant_mode)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Failed to generate assistant response: {error}") from error
        if result is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return MessageCreateResponse(**result)

    @app.get("/api/chats/{chat_id}/download", response_model=ChatDownloadResponse, responses={404: {"model": ErrorResponse}})
    def download_chat(
        chat_id: str,
        response: Response,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatDownloadResponse:
        payload = service.download_chat(auth.user, chat_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        safe_name = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in payload.chat_name)
        response.headers["Content-Disposition"] = f'attachment; filename="{safe_name or "chat"}-{chat_id}.json"'
        return payload

    @app.get("/api/library/files", response_model=LibraryListResponse)
    def list_library_files(
        include_other_users: bool = Query(default=False),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LibraryListResponse:
        return service.list_library_files(auth.user, include_other_users=include_other_users)

    @app.post("/api/library/files/upload", response_model=LibraryUploadResponse, responses={422: {"model": ErrorResponse}})
    async def upload_library_files(
        files: list[UploadFile] = File(...),
        tags_by_file: str | None = Form(default=None),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LibraryUploadResponse:
        uploads = [UploadFilePayload(file_name=file.filename or "upload.bin", content=await file.read()) for file in files]
        try:
            return LibraryUploadResponse(**service.upload_library_files(auth.user, uploads, tags_by_file))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.patch(
        "/api/library/files/{file_id}",
        response_model=LibraryFileRead,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    def update_library_file(
        file_id: int,
        payload: LibraryFileUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LibraryFileRead:
        if payload.is_enabled is None:
            raise HTTPException(status_code=422, detail="At least one file field must be updated")
        try:
            record = service.update_library_file(auth.user, file_id, is_enabled=payload.is_enabled)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Library file not found")
        return record

    @app.delete("/api/library/files/{file_id}", response_model=LibraryFileRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def delete_library_file(
        file_id: int,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LibraryFileRead:
        try:
            record = service.delete_library_file(auth.user, file_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Library file not found")
        return record

    @app.get("/api/settings", response_model=SettingsRead)
    def get_runtime_settings(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> SettingsRead:
        return service.get_settings(auth.user)

    @app.patch("/api/settings", response_model=SettingsRead, responses={422: {"model": ErrorResponse}})
    def update_runtime_settings(
        payload: SettingsUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> SettingsRead:
        try:
            return service.update_settings(auth.user, payload)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/personalization", response_model=PersonalizationRead)
    def get_personalization(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> PersonalizationRead:
        return service.get_personalization(auth.user)

    @app.patch("/api/personalization", response_model=PersonalizationRead)
    def update_personalization(
        payload: PersonalizationUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> PersonalizationRead:
        return service.update_personalization(auth.user, payload)

    return app
