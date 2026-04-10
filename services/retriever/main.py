from __future__ import annotations

import uuid
from pathlib import Path

from dotenv import load_dotenv

from services.common.config import get_settings
from services.common.logging import configure_logging
from services.embedder.embedding import EmbeddingClient
from services.retriever.chat_history import ChatHistoryService
from services.retriever.llm_client import LlmClient
from services.retriever.postgres_client import RetrieverPostgresClient
from services.retriever.prompt_builder import PromptBuilder
from services.retriever.qdrant_client import RetrieverQdrantClient
from services.retriever.repositories.chat_repository import ChatRepository
from services.retriever.retriever import RetrievalService
from services.retriever.source_formatter import format_sources
from services.retriever.services.chat_naming import generate_chat_name


def main() -> None:
    load_dotenv()
    settings = get_settings()
    configure_logging(settings.log_level)
    prompts_dir = Path(__file__).resolve().parents[2] / "prompts"

    postgres_client = RetrieverPostgresClient(settings.database_url)
    postgres_client.initialize()
    chat_repository = ChatRepository(postgres_client)

    retrieval_service = RetrievalService(
        embedding_client=EmbeddingClient(
            model=settings.embedding_model,
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            max_input_tokens=settings.embedding_max_input_tokens,
        ),
        qdrant_store=RetrieverQdrantClient(settings.qdrant_url, settings.qdrant_collection),
        score_threshold=settings.retrieval_score_threshold,
        min_results=settings.retrieval_min_results,
        max_results=settings.retrieval_max_results,
    )
    llm_client = LlmClient(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
    )
    prompt_builder = PromptBuilder(prompts_dir)
    history_service = ChatHistoryService(postgres_client, settings.history_limit)
    users = [user for user in postgres_client.list_users() if user.status == "active"]
    if not users:
        raise RuntimeError("No active users available for CLI session")
    user_id = users[0].id

    session_id = str(uuid.uuid4())
    chat_repository.ensure_chat(user_id, session_id, generate_chat_name())
    print(f"RAG session: {session_id}")
    print("Type 'exit' to quit.")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = postgres_client.add_chat_message(session_id, user_id, "user", user_input)
        history = history_service.fetch(session_id, user_id=user_id, exclude_message_id=user_message.id)
        retrieved_chunks = retrieval_service.retrieve(user_input, user_id=user_id, chat_id=session_id)
        messages = prompt_builder.build_simple_messages(user_message=user_input, history=history, retrieved_chunks=retrieved_chunks)
        response = llm_client.invoke(messages)
        assistant_message = postgres_client.add_chat_message(session_id, user_id, "assistant", response)
        postgres_client.add_retrieval_logs(
            assistant_message_id=assistant_message.id,
            user_message_id=user_message.id,
            session_id=session_id,
            user_id=user_id,
            used_chunks=retrieved_chunks,
        )
        print(f"AI: {response}")
        print()
        print(format_sources(retrieved_chunks))


if __name__ == "__main__":
    main()
