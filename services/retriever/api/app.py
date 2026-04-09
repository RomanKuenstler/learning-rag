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
    SystemStatusResponse,
)
from services.retriever.schemas.learning import (
    CourseImportResponse,
    CourseListResponse,
    CourseTemplateResponse,
    LearningNodeProgressUpdateRequest,
    LearningLessonCreateRequest,
    LearningLessonRead,
    LearningLessonReorderRequest,
    LearningLessonUpdateRequest,
    LearningModuleCreateRequest,
    LearningModuleRead,
    LearningModuleReorderRequest,
    LearningModuleUpdateRequest,
    LearningPathCreateRequest,
    LearningPathListResponse,
    LearningPathRead,
    LearningPathUpdateRequest,
)
from services.retriever.schemas.learning_profile import (
    LearningGoalCreateRequest,
    LearningGoalRead,
    LearningGoalUpdateRequest,
    LearningPreferencesRead,
    LearningPreferencesUpdateRequest,
    LearningProfileBundleRead,
    LearningProfileContextRead,
    LearningProfileContextUpdateRequest,
)
from services.retriever.schemas.diagnostics import (
    DiagnosticAnswerUpsertRequest,
    DiagnosticAttemptDetailsRead,
    DiagnosticAttemptStartResponse,
    DiagnosticAttemptSummaryRead,
    DiagnosticCatalogRead,
    DiagnosticDefinitionRead,
    DiagnosticResultRead,
    ExplanationFeedbackCreateRequest,
    ExplanationFeedbackRead,
    LearningStateCheckCreateRequest,
    LearningStateCheckRead,
)
from services.retriever.schemas.ksa import KSAProfileRead
from services.retriever.schemas.ksa_assessment import (
    KSAAssessmentAttemptRead,
    KSAAssessmentAnswersUpsertRequest,
    KSAAssessmentDefinitionRead,
    KSAAssessmentStartResponse,
)
from services.retriever.schemas.ksa_drills import (
    KSADrillAnswersUpsertRequest,
    KSADrillAttemptsRead,
    KSADrillAttemptRead,
    KSADrillAttemptStartRequest,
    KSADrillAttemptStartResponse,
    KSADrillTopicsRead,
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

    @app.get("/api/system/status", response_model=SystemStatusResponse)
    def system_status(
        auth: AuthContext = Depends(get_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> SystemStatusResponse:
        return service.get_system_status(auth)

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

    @app.post("/api/chats", response_model=ChatRead, responses={403: {"model": ErrorResponse}})
    def create_chat(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            return service.create_chat(auth.user)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get("/api/chats", response_model=list[ChatRead], responses={403: {"model": ErrorResponse}})
    def list_chats(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[ChatRead]:
        try:
            return service.list_chats(auth.user)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get("/api/chats/archived", response_model=list[ChatRead], responses={403: {"model": ErrorResponse}})
    def list_archived_chats(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[ChatRead]:
        try:
            return service.list_archived_chats(auth.user)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get("/api/chats/{chat_id}", response_model=ChatRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def get_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            chat = service.get_chat(auth.user, chat_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.patch("/api/chats/{chat_id}", response_model=ChatRead, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def rename_chat(
        chat_id: str,
        payload: ChatUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            chat = service.rename_chat(auth.user, chat_id, payload.chat_name)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.patch("/api/chats/{chat_id}/archive", response_model=ChatRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def archive_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            chat = service.archive_chat(auth.user, chat_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.patch("/api/chats/{chat_id}/unarchive", response_model=ChatRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def unarchive_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            chat = service.unarchive_chat(auth.user, chat_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.delete("/api/chats/{chat_id}", response_model=ChatRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def delete_chat(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatRead:
        try:
            chat = service.delete_chat(auth.user, chat_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat

    @app.get("/api/gpts", response_model=list[GptRead], responses={403: {"model": ErrorResponse}})
    def list_gpts(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[GptRead]:
        try:
            return service.list_gpts(auth.user)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.post("/api/gpts", response_model=GptRead, responses={422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def create_gpt(
        payload: GptCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptRead:
        try:
            return service.create_gpt(auth.user, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/gpts/{gpt_id}", response_model=GptRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def get_gpt(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptRead:
        try:
            record = service.get_gpt(auth.user, gpt_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.patch("/api/gpts/{gpt_id}", response_model=GptRead, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def update_gpt(
        gpt_id: str,
        payload: GptUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptRead:
        try:
            record = service.update_gpt(auth.user, gpt_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.delete("/api/gpts/{gpt_id}", response_model=GptDeleteResponse, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def delete_gpt(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptDeleteResponse:
        try:
            record = service.delete_gpt(auth.user, gpt_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.post("/api/gpts/preview/messages", response_model=MessageCreateResponse, responses={422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def preview_gpt_message(
        payload: GptPreviewMessageCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> MessageCreateResponse:
        try:
            return MessageCreateResponse(**service.preview_gpt_message(auth.user, payload))
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/gpts/{gpt_id}/chat", response_model=GptChatRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def get_gpt_chat(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptChatRead:
        try:
            record = service.get_gpt_chat(auth.user, gpt_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.delete("/api/gpts/{gpt_id}/chat", response_model=GptChatRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def clear_gpt_chat(
        gpt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> GptChatRead:
        try:
            record = service.clear_gpt_chat(auth.user, gpt_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return record

    @app.post("/api/gpts/{gpt_id}/messages", response_model=MessageCreateResponse, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
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
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Failed to generate assistant response: {error}") from error
        if result is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        return MessageCreateResponse(**result)

    @app.get("/api/gpts/{gpt_id}/download", response_model=ChatDownloadResponse, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def download_gpt_chat(
        gpt_id: str,
        response: Response,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatDownloadResponse:
        try:
            payload = service.download_gpt_chat(auth.user, gpt_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if payload is None:
            raise HTTPException(status_code=404, detail="GPT not found")
        safe_name = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in payload.chat_name)
        response.headers["Content-Disposition"] = f'attachment; filename="{safe_name or "gpt"}-{gpt_id}.json"'
        return payload

    @app.get("/api/chats/{chat_id}/messages", response_model=list[MessageRead], responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def get_messages(
        chat_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[MessageRead]:
        try:
            chat = service.get_chat(auth.user, chat_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return service.get_chat_messages(auth.user, chat_id)

    @app.get("/api/learning-paths", response_model=LearningPathListResponse)
    def list_learning_paths(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPathListResponse:
        return service.list_learning_paths(auth.user)

    @app.get("/api/courses", response_model=CourseListResponse)
    def list_courses(
        search: str = Query(default=""),
        scope: str | None = Query(default=None, pattern="^(global|user)$"),
        status: str | None = Query(default=None, pattern="^(draft|published|archived)$"),
        owner_user_id: int | None = Query(default=None, ge=1),
        sort: str = Query(default="updated_desc"),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> CourseListResponse:
        return service.list_courses(
            auth.user,
            search=search,
            scope=scope,
            status=status,
            owner_user_id=owner_user_id,
            sort=sort,
        )

    @app.get("/api/courses/template", response_model=CourseTemplateResponse)
    def get_course_template(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> CourseTemplateResponse:
        _ = auth
        return service.get_course_template()

    @app.post("/api/courses/import", response_model=CourseImportResponse, responses={422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    async def import_courses(
        files: list[UploadFile] = File(...),
        scopes_by_file: str | None = Form(default=None),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> CourseImportResponse:
        uploads = [UploadFilePayload(file_name=file.filename or "course.json", content=await file.read()) for file in files]
        try:
            return service.import_courses_from_uploads(auth.user, uploads, scopes_by_file)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/learning-paths", response_model=LearningPathRead, responses={403: {"model": ErrorResponse}})
    def create_learning_path(
        payload: LearningPathCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPathRead:
        try:
            return service.create_learning_path(auth.user, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

    @app.get("/api/learning-paths/{learning_path_id}", response_model=LearningPathRead, responses={404: {"model": ErrorResponse}})
    def get_learning_path(
        learning_path_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPathRead:
        record = service.get_learning_path(auth.user, learning_path_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Learning path not found")
        return record

    @app.put(
        "/api/learning-paths/{learning_path_id}/nodes/{node_id}/progress",
        response_model=LearningPathRead,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    def update_learning_node_progress(
        learning_path_id: str,
        node_id: str,
        payload: LearningNodeProgressUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPathRead:
        try:
            updated = service.update_learning_node_progress(auth.user, learning_path_id, node_id, payload)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if updated is None:
            raise HTTPException(status_code=404, detail="Learning path or node not found")
        return updated

    @app.patch("/api/learning-paths/{learning_path_id}", response_model=LearningPathRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def update_learning_path(
        learning_path_id: str,
        payload: LearningPathUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPathRead:
        try:
            record = service.update_learning_path(auth.user, learning_path_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning path not found")
        return record

    @app.delete("/api/learning-paths/{learning_path_id}", response_model=LearningPathRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def delete_learning_path(
        learning_path_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPathRead:
        try:
            record = service.delete_learning_path(auth.user, learning_path_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning path not found")
        return record

    @app.post("/api/learning-paths/{learning_path_id}/modules", response_model=LearningModuleRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def create_learning_module(
        learning_path_id: str,
        payload: LearningModuleCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningModuleRead:
        try:
            record = service.create_learning_module(auth.user, learning_path_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning path not found")
        return record

    @app.patch("/api/learning-paths/{learning_path_id}/modules/reorder", response_model=list[LearningModuleRead], responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def reorder_learning_modules(
        learning_path_id: str,
        payload: LearningModuleReorderRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[LearningModuleRead]:
        try:
            records = service.reorder_learning_modules(auth.user, learning_path_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if records is None:
            raise HTTPException(status_code=404, detail="Learning path not found")
        return records

    @app.patch("/api/learning-modules/{module_id}", response_model=LearningModuleRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def update_learning_module(
        module_id: str,
        payload: LearningModuleUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningModuleRead:
        try:
            record = service.update_learning_module(auth.user, module_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning module not found")
        return record

    @app.delete("/api/learning-modules/{module_id}", response_model=LearningModuleRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def delete_learning_module(
        module_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningModuleRead:
        try:
            record = service.delete_learning_module(auth.user, module_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning module not found")
        return record

    @app.post("/api/learning-modules/{module_id}/lessons", response_model=LearningLessonRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def create_learning_lesson(
        module_id: str,
        payload: LearningLessonCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningLessonRead:
        try:
            record = service.create_learning_lesson(auth.user, module_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning module not found")
        return record

    @app.patch("/api/learning-modules/{module_id}/lessons/reorder", response_model=list[LearningLessonRead], responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def reorder_learning_lessons(
        module_id: str,
        payload: LearningLessonReorderRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[LearningLessonRead]:
        try:
            records = service.reorder_learning_lessons(auth.user, module_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if records is None:
            raise HTTPException(status_code=404, detail="Learning module not found")
        return records

    @app.patch("/api/learning-lessons/{lesson_id}", response_model=LearningLessonRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def update_learning_lesson(
        lesson_id: str,
        payload: LearningLessonUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningLessonRead:
        try:
            record = service.update_learning_lesson(auth.user, lesson_id, payload)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning lesson not found")
        return record

    @app.delete("/api/learning-lessons/{lesson_id}", response_model=LearningLessonRead, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def delete_learning_lesson(
        lesson_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningLessonRead:
        try:
            record = service.delete_learning_lesson(auth.user, lesson_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Learning lesson not found")
        return record

    @app.get("/api/learning-profile", response_model=LearningProfileBundleRead)
    def get_learning_profile_bundle(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningProfileBundleRead:
        return service.get_learning_profile_bundle(auth.user)

    @app.get("/api/learning-profile/ksa", response_model=KSAProfileRead)
    def get_ksa_profile(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAProfileRead:
        return service.get_ksa_profile(auth.user)

    @app.get("/api/ksa/assessment/definition", response_model=KSAAssessmentDefinitionRead)
    def get_ksa_assessment_definition(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAAssessmentDefinitionRead:
        return service.get_ksa_assessment_definition(auth.user)

    @app.post("/api/ksa/assessment/attempts", response_model=KSAAssessmentStartResponse)
    def start_ksa_assessment(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAAssessmentStartResponse:
        return service.start_ksa_assessment(auth.user)

    @app.get("/api/ksa/assessment/attempts/latest", response_model=KSAAssessmentAttemptRead, responses={404: {"model": ErrorResponse}})
    def get_latest_ksa_assessment_attempt(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAAssessmentAttemptRead:
        attempt = service.get_latest_ksa_assessment_attempt(auth.user)
        if attempt is None:
            raise HTTPException(status_code=404, detail="KSA assessment attempt not found")
        return attempt

    @app.get("/api/ksa/assessment/attempts/{attempt_id}", response_model=KSAAssessmentAttemptRead, responses={404: {"model": ErrorResponse}})
    def get_ksa_assessment_attempt(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAAssessmentAttemptRead:
        attempt = service.get_ksa_assessment_attempt(auth.user, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="KSA assessment attempt not found")
        return attempt

    @app.put("/api/ksa/assessment/attempts/{attempt_id}/answers", response_model=KSAAssessmentAttemptRead, responses={404: {"model": ErrorResponse}})
    def upsert_ksa_assessment_answers(
        attempt_id: str,
        payload: KSAAssessmentAnswersUpsertRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAAssessmentAttemptRead:
        attempt = service.upsert_ksa_assessment_answers(auth.user, attempt_id, payload)
        if attempt is None:
            raise HTTPException(status_code=404, detail="KSA assessment attempt not found")
        return attempt

    @app.post("/api/ksa/assessment/attempts/{attempt_id}/complete", response_model=KSAProfileRead, responses={404: {"model": ErrorResponse}})
    def complete_ksa_assessment(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAProfileRead:
        profile = service.complete_ksa_assessment(auth.user, attempt_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="KSA assessment attempt not found")
        return profile

    @app.get("/api/ksa/drills/topics", response_model=KSADrillTopicsRead)
    def list_ksa_drill_topics(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSADrillTopicsRead:
        return service.list_ksa_drill_topics(auth.user)

    @app.get("/api/ksa/drills/attempts", response_model=KSADrillAttemptsRead)
    def list_ksa_drill_attempts(
        limit: int = Query(default=25, ge=1, le=100),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSADrillAttemptsRead:
        return service.list_ksa_drill_attempts(auth.user, limit=limit)

    @app.post("/api/ksa/drills/attempts", response_model=KSADrillAttemptStartResponse)
    def start_ksa_drill_attempt(
        payload: KSADrillAttemptStartRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSADrillAttemptStartResponse:
        return service.start_ksa_drill_attempt(auth.user, payload)

    @app.get("/api/ksa/drills/attempts/latest", response_model=KSADrillAttemptRead, responses={404: {"model": ErrorResponse}})
    def get_latest_ksa_drill_attempt(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSADrillAttemptRead:
        attempt = service.get_latest_ksa_drill_attempt(auth.user)
        if attempt is None:
            raise HTTPException(status_code=404, detail="KSA drill attempt not found")
        return attempt

    @app.get("/api/ksa/drills/attempts/{attempt_id}", response_model=KSADrillAttemptRead, responses={404: {"model": ErrorResponse}})
    def get_ksa_drill_attempt(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSADrillAttemptRead:
        attempt = service.get_ksa_drill_attempt(auth.user, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="KSA drill attempt not found")
        return attempt

    @app.put("/api/ksa/drills/attempts/{attempt_id}/answers", response_model=KSADrillAttemptRead, responses={404: {"model": ErrorResponse}})
    def upsert_ksa_drill_answers(
        attempt_id: str,
        payload: KSADrillAnswersUpsertRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSADrillAttemptRead:
        attempt = service.upsert_ksa_drill_answers(auth.user, attempt_id, payload)
        if attempt is None:
            raise HTTPException(status_code=404, detail="KSA drill attempt not found")
        return attempt

    @app.post("/api/ksa/drills/attempts/{attempt_id}/complete", response_model=KSAProfileRead, responses={404: {"model": ErrorResponse}})
    def complete_ksa_drill_attempt(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> KSAProfileRead:
        profile = service.complete_ksa_drill_attempt(auth.user, attempt_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="KSA drill attempt not found")
        return profile

    @app.patch("/api/learning-profile/preferences", response_model=LearningPreferencesRead)
    def update_learning_preferences(
        payload: LearningPreferencesUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningPreferencesRead:
        return service.update_learning_preferences(auth.user, payload)

    @app.patch("/api/learning-profile/context", response_model=LearningProfileContextRead)
    def update_learning_context(
        payload: LearningProfileContextUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningProfileContextRead:
        return service.update_learning_context(auth.user, payload)

    @app.post("/api/learning-profile/goals", response_model=LearningGoalRead)
    def create_learning_goal(
        payload: LearningGoalCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningGoalRead:
        return service.create_learning_goal(auth.user, payload)

    @app.patch("/api/learning-profile/goals/{goal_id}", response_model=LearningGoalRead, responses={404: {"model": ErrorResponse}})
    def update_learning_goal(
        goal_id: str,
        payload: LearningGoalUpdateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningGoalRead:
        updated = service.update_learning_goal(auth.user, goal_id, payload)
        if updated is None:
            raise HTTPException(status_code=404, detail="Learning goal not found")
        return updated

    @app.delete("/api/learning-profile/goals/{goal_id}", response_model=LearningGoalRead, responses={404: {"model": ErrorResponse}})
    def delete_learning_goal(
        goal_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningGoalRead:
        deleted = service.delete_learning_goal(auth.user, goal_id)
        if deleted is None:
            raise HTTPException(status_code=404, detail="Learning goal not found")
        return deleted

    @app.get("/api/diagnostics/definitions", response_model=DiagnosticCatalogRead)
    def list_diagnostic_definitions(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticCatalogRead:
        _ = auth
        return service.list_diagnostic_definitions()

    @app.get("/api/diagnostics/definitions/{diagnostic_type}", response_model=DiagnosticDefinitionRead, responses={404: {"model": ErrorResponse}})
    def get_diagnostic_definition(
        diagnostic_type: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticDefinitionRead:
        _ = auth
        definition = service.get_diagnostic_definition(diagnostic_type.upper())
        if definition is None:
            raise HTTPException(status_code=404, detail="Diagnostic definition not found")
        return definition

    @app.post("/api/diagnostics/attempts", response_model=DiagnosticAttemptStartResponse)
    def start_diagnostic_attempt(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticAttemptStartResponse:
        return service.start_diagnostic_attempt(auth.user)

    @app.get("/api/diagnostics/attempts", response_model=list[DiagnosticAttemptSummaryRead])
    def list_diagnostic_attempts(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[DiagnosticAttemptSummaryRead]:
        return service.list_diagnostic_attempts(auth.user)

    @app.delete("/api/diagnostics/attempts/{attempt_id}", response_model=DiagnosticAttemptSummaryRead, responses={404: {"model": ErrorResponse}})
    def delete_diagnostic_attempt(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticAttemptSummaryRead:
        deleted = service.delete_diagnostic_attempt(auth.user, attempt_id)
        if deleted is None:
            raise HTTPException(status_code=404, detail="Diagnostic attempt not found")
        return deleted

    @app.get("/api/diagnostics/attempts/latest", response_model=DiagnosticAttemptDetailsRead, responses={404: {"model": ErrorResponse}})
    def get_latest_diagnostic_attempt(
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticAttemptDetailsRead:
        attempt = service.get_latest_diagnostic_attempt(auth.user)
        if attempt is None:
            raise HTTPException(status_code=404, detail="No diagnostic attempt found")
        return attempt

    @app.get("/api/diagnostics/attempts/{attempt_id}", response_model=DiagnosticAttemptDetailsRead, responses={404: {"model": ErrorResponse}})
    def get_diagnostic_attempt(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticAttemptDetailsRead:
        attempt = service.get_diagnostic_attempt(auth.user, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="Diagnostic attempt not found")
        return attempt

    @app.put("/api/diagnostics/attempts/{attempt_id}/answers", response_model=DiagnosticAttemptDetailsRead, responses={404: {"model": ErrorResponse}})
    def upsert_diagnostic_answers(
        attempt_id: str,
        payload: DiagnosticAnswerUpsertRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticAttemptDetailsRead:
        attempt = service.upsert_diagnostic_answers(auth.user, attempt_id, payload)
        if attempt is None:
            raise HTTPException(status_code=404, detail="Diagnostic attempt not found")
        return attempt

    @app.post("/api/diagnostics/attempts/{attempt_id}/complete", response_model=DiagnosticResultRead, responses={404: {"model": ErrorResponse}})
    def complete_diagnostic_attempt(
        attempt_id: str,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> DiagnosticResultRead:
        result = service.complete_diagnostic_attempt(auth.user, attempt_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Diagnostic attempt not found")
        return result

    @app.post("/api/learning-state-checks", response_model=LearningStateCheckRead)
    def create_learning_state_check(
        payload: LearningStateCheckCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> LearningStateCheckRead:
        return service.create_learning_state_check(auth.user, payload)

    @app.get("/api/learning-state-checks", response_model=list[LearningStateCheckRead])
    def list_learning_state_checks(
        limit: int = Query(default=20, ge=1, le=200),
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> list[LearningStateCheckRead]:
        return service.list_learning_state_checks(auth.user, limit=limit)

    @app.post("/api/explanation-feedback", response_model=ExplanationFeedbackRead)
    def create_explanation_feedback(
        payload: ExplanationFeedbackCreateRequest,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ExplanationFeedbackRead:
        return service.create_explanation_feedback(auth.user, payload)

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
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
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
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Failed to generate assistant response: {error}") from error
        if result is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return MessageCreateResponse(**result)

    @app.get("/api/chats/{chat_id}/download", response_model=ChatDownloadResponse, responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
    def download_chat(
        chat_id: str,
        response: Response,
        auth: AuthContext = Depends(get_app_auth_context),
        service: RetrieverAppService = Depends(get_retriever_service),
    ) -> ChatDownloadResponse:
        try:
            payload = service.download_chat(auth.user, chat_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
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

    @app.on_event("startup")
    def warm_retriever_service() -> None:
        # Initialize service eagerly so bootstrap jobs (users/courses sync) run
        # on container startup, not only after the first API request.
        get_retriever_service()

    return app
