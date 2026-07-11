import os
import time
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchAny
from typing import List, Optional
import asyncio

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://bothub.chat/api/v2/openai/v1")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.15"))
QDRANT_RETRIES = int(os.getenv("QDRANT_RETRIES", "20"))
QDRANT_RETRY_DELAY = float(os.getenv("QDRANT_RETRY_DELAY", "1.0"))

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не указан в .env")

# Синхронный клиент для операций с БД
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    check_compatibility=False,
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    temperature=0.1,
    streaming=True,
)

COLLECTION_NAME = "knowledge_base"
VECTOR_SIZE = 1536  # text-embedding-3-small размер


def collection_exists_safe(retries: int = QDRANT_RETRIES) -> bool:
    """Проверить коллекцию с коротким retry, если Qdrant еще не готов."""
    last_error = None
    for attempt in range(retries):
        try:
            return client.collection_exists(COLLECTION_NAME)
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(QDRANT_RETRY_DELAY)

    print(f"Qdrant недоступен: {last_error}")
    return False


def ensure_collection_exists():
    """Создать коллекцию если не существует"""
    if not collection_exists_safe():
        try:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
        except Exception as e:
            # Collection might have been created by another thread
            print(f"Не удалось создать коллекцию Qdrant: {e}")


def clear_collection():
    """Очистить коллекцию"""
    if collection_exists_safe():
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception as e:
            print(f"Не удалось удалить коллекцию Qdrant: {e}")


def list_sources():
    """Вывести абсолютно все уникальные источники, которые реально лежат в Qdrant."""
    if not collection_exists_safe():
        print("Коллекция knowledge_base не найдена или Qdrant недоступен")
        return []

    all_sources = set()
    next_page_offset = None

    # 1. Цикл пагинации: листаем страницы Qdrant до самого конца
    while True:
        points, next_page_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,  # Качаем порциями по 100, чтобы не забивать память
            offset=next_page_offset,
            with_payload=True,
            with_vectors=False,  # Экономим трафик, векторы нам не нужны
        )

        # 2. Собираем источники. Множество (set) само на лету удаляет дубликаты
        for point in points:
            payload = point.payload or {}
            source = payload.get("metadata", {}).get("source") or payload.get("source")
            if source:
                all_sources.add(source)

        # Если Qdrant вернул next_page_offset = None, значит данные кончились
        if next_page_offset is None:
            break

    # 3. Сортируем полученный результат по алфавиту
    sorted_sources = sorted(all_sources)

    for source in sorted_sources:
        print(source)

    return sorted_sources


def add_documents_to_db(text: str, metadata: dict):
    """Добавить документ в базу знаний (синхронная функция)"""
    ensure_collection_exists()

    # Разбиваем текст на чанки
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    docs = text_splitter.create_documents([text], metadatas=[metadata])

    # Добавляем в Qdrant
    vs = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    vs.add_documents(docs)


def _search_relevant_docs(vs: QdrantVectorStore, query: str, k: int):
    """Вернуть только достаточно релевантные документы для ответа."""
    results = vs.similarity_search_with_score(query, k=k)
    return [doc for doc, score in results if score >= MIN_RELEVANCE_SCORE]


def _search_docs_fallback(vs: QdrantVectorStore, query: str, k: int):
    """Fallback для явно названных ЖК, если score-фильтр оказался слишком строгим."""
    return vs.similarity_search(query, k=k)


def _build_prompt_and_search(query: str, history: Optional[List] = None):
    """
    Выполняет поиск по Qdrant и возвращает:
        context: str | None
        projects: list[str]
        unique_docs: list[Document]
    """

    # ---------------------------------------------------------
    # Проверка коллекции
    # ---------------------------------------------------------
    if not client.collection_exists(collection_name=COLLECTION_NAME):
        print(f"DEBUG: Коллекция '{COLLECTION_NAME}' не существует")
        return None, [], []

    # ---------------------------------------------------------
    # Формирование поискового запроса
    # ---------------------------------------------------------
    search_query = query.strip()

    if history:
        prev_questions = [
            msg[1]
            for msg in history[-4:]
            if isinstance(msg, (list, tuple))
            and len(msg) >= 2
            and msg[0] == "user"
        ]

        if prev_questions:
            search_query = " ".join(prev_questions[-2:]) + " " + query

    print(f"\nDEBUG: search_query = {search_query}")

    # ---------------------------------------------------------
    # Подключение к VectorStore
    # ---------------------------------------------------------
    vs = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    # ---------------------------------------------------------
    # Определяем проект
    # ---------------------------------------------------------
    query_lower = query.lower()

    projects = []

    if any(x in query_lower for x in ["алиса", "alisa"]):
        projects.append("Алиса")

    if any(x in query_lower for x in ["бестселлер", "bestseller"]):
        projects.append("Бестселлер")

    print(f"DEBUG: projects = {projects}")

    # ---------------------------------------------------------
    # Создаем фильтр
    # ---------------------------------------------------------
    qdrant_filter = None

    if projects:
        qdrant_filter = Filter(
            must=[
                FieldCondition(
                    key="project",
                    match=MatchAny(any=projects),
                )
            ]
        )

    # ---------------------------------------------------------
    # Поиск
    # ---------------------------------------------------------
    try:
        if qdrant_filter:
            docs = vs.similarity_search(
                search_query,
                k=12,
                filter=qdrant_filter,
            )

            print(f"DEBUG: найдено с фильтром = {len(docs)}")
        else:
            docs = []

        # fallback
        if not docs:
            print("DEBUG: fallback без фильтра")

            docs = vs.similarity_search(
                search_query,
                k=12,
            )

            print(f"DEBUG: найдено без фильтра = {len(docs)}")

    except Exception as e:
        print(f"DEBUG: ошибка поиска: {e}")
        return None, projects, []

    # ---------------------------------------------------------
    # Логируем найденные документы
    # ---------------------------------------------------------
    if docs:
        for i, doc in enumerate(docs):
            print("\n" + "=" * 80)
            print(f"Документ {i + 1}")

            print("metadata:")
            print(doc.metadata)

            print("content:")
            print(doc.page_content[:300])

    # ---------------------------------------------------------
    # Дедупликация
    # ---------------------------------------------------------
    seen = set()
    unique_docs = []

    for doc in docs:
        text = doc.page_content.strip()

        if text and text not in seen:
            seen.add(text)
            unique_docs.append(doc)

    print(f"\nDEBUG: после дедупликации = {len(unique_docs)}")

    if not unique_docs:
        return None, projects, []

    # ---------------------------------------------------------
    # Формируем контекст
    # ---------------------------------------------------------
    context_parts = []

    for doc in unique_docs:
        source = doc.metadata.get("source", "unknown")
        project = doc.metadata.get("project", "unknown")

        context_parts.append(
            f"""Источник: {source}
Проект: {project}

{doc.page_content}
"""
        )

    context = "\n\n------------------------\n\n".join(context_parts)

    print("\n" + "=" * 80)
    print("КОНТЕКСТ ДЛЯ LLM")
    print("=" * 80)
    print(context[:5000])
    print("=" * 80)

    return context, projects, unique_docs


async def get_answer_stream(query: str, history: Optional[List] = None):
    """Генератор для стриминга ответа от LLM с реальным streaming"""
    # Run search in thread to avoid blocking
    context, projects, docs = await asyncio.to_thread(
        _build_prompt_and_search, query, history
    )

    if context is None:
        yield "Извините, я не нашел информации по вашему вопросу. Пожалуйста, свяжитесь с менеджером."
        return

    # Build messages for the prompt
    messages = [
        (
            "system",
            "Ты — ассистент агента по недвижимости. Отвечай на русском языке, подробно и по делу. Используй ТОЛЬКО информацию из контекста. Если данных нет — скажи, что не знаешь. Никогда не выдумывай.",
        ),
    ]

    if history:
        for role, text in history[-6:]:
            messages.append(("human" if role == "user" else "ai", text))

    projects_str = ", ".join(projects) if projects else "..."
    user_message = (
        f"Вопрос: {query}\n\n"
        f"ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:\n{context}\n\n"
        f"Правила:\n"
        f"- Если в информации выше есть данные по вопросу — ответь на основе этих данных.\n"
        f"- Если вопрос про несколько ЖК ({projects_str}) — дай информацию по КАЖДОМУ.\n"
        f"- Если информации нет — скажи, что не знаешь.\n"
        f"- Не выдумывай ничего.\n"
        f"- СТРОГОЕ ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM HTML:\n"
        f"  1. Пиши ответ БЕЗ использования Markdown (ЗАПРЕЩЕНЫ символы **, #, _, `).\n"
        f"  2. Для выделения используй исключительно HTML-теги: <b>жирный</b>, <i>курсив</i>, <code>код</code>.\n"
        f"  3. Всегда закрывай открытые теги (недопустимо оставить <b> без </b>).\n"
        f"  4. Для списков используй обычный перенос строки и дефисы. Теги <ul>, <li> и <br> ЗАПРЕЩЕНЫ.\n"
        f"  5. Если не уверен в валидности HTML-тегов, отдавай чистый текст без какого-либо форматирования.\n\n"
        f"Ответ:"
    )

    messages.append(("human", user_message))

    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm

    # Use astream for real streaming
    async for chunk in chain.astream({}):
        if hasattr(chunk, "content"):
            yield chunk.content
        else:
            yield str(chunk)


async def get_answer(query: str, history: Optional[List] = None) -> str:
    """Асинхронный ответ (обертка над синхронным)"""
    context, projects, docs = await asyncio.to_thread(
        _build_prompt_and_search, query, history
    )

    if context is None:
        return "Извините, я не нашел информации по вашему вопросу. Пожалуйста, свяжитесь с менеджером."

    # Build messages for the prompt
    messages = [
        (
            "system",
            "Ты — ассистент агента по недвижимости. Отвечай на русском языке, подробно и по делу. Используй ТОЛЬКО информацию из контекста. Если данных нет — скажи, что не знаешь. Никогда не выдумывай.",
        ),
    ]

    if history:
        for role, text in history[-6:]:
            messages.append(("human" if role == "user" else "ai", text))

    projects_str = ", ".join(projects) if projects else "..."
    user_message = (
        f"Вопрос: {query}\n\n"
        f"ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:\n{context}\n\n"
        f"Правила:\n"
        f"- Если в информации выше есть данные по вопросу — ответь на основе этих данных\n"
        f"- Если вопрос про несколько ЖК ({projects_str}) — дай информацию по КАЖДОМУ\n"
        f"- Если информации нет — скажи, что не знаешь\n"
        f"- Не выдумывай ничего\n\n"
        f"Ответ:"
    )

    messages.append(("human", user_message))

    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm

    answer = await chain.ainvoke({})

    content = answer.content if hasattr(answer, "content") else str(answer)

    if not content or len(content.strip()) < 10:
        return "Извините, я не нашел информации. Пожалуйста, свяжитесь с менеджером."

    return content
