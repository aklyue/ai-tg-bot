import os
import time
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
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
    """Поиск и подготовка промпта (синхронный)"""
    if not collection_exists_safe():
        return None, None, None

    search_query = query
    if history:
        prev_questions = [msg[1] for msg in history[-4:] if msg[0] == "user"]
        if prev_questions:
            search_query = " ".join(prev_questions[-2:]) + " " + query

    # Поиск
    vs = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    query_lower = query.lower()
    projects = []
    if any(word in query_lower for word in ["бестселлер", "bestseller"]):
        projects.append("Бестселлер")
    if any(word in query_lower for word in ["алиса", "alisa"]):
        projects.append("Алиса")

    docs = []
    try:
        if len(projects) >= 2:
            for project in projects:
                # 1. Определяем, кто конкурент для текущего цикла
                other_project = "Алиса" if project == "Бестселлер" else "Бестселлер"
                
                # 2. Полностью вырезаем конкурента из запроса, чтобы не косило вектор
                # Строка 'Сравни ипотеку ЖК Алиса и ЖК Бестселлер' превратится в 'Сравни ипотеку ЖК '
                clean_query = query.lower().replace(other_project.lower(), "").strip()
                
                # 3. Собираем идеальный прицельный запрос для базы
                # Получится: 'ЖК Бестселлер Сравни ипотеку'
                project_query = f"ЖК {project} {clean_query}"
                
                results = _search_relevant_docs(vs, project_query, k=6)
                fallback_results = _search_docs_fallback(vs, project_query, k=6)
                for doc in fallback_results:
                    if doc not in results:
                        results.append(doc)
                docs.extend(results)
        else:
            # ИСПРАВЛЕНИЕ: Если упомянут ОДИН конкретный ЖК (например, Бестселлер)
            if projects:
                # Первым делом жестко ищем именно этот ЖК, чтобы он был в ТОПе списка и его не отрезало
                docs = _search_relevant_docs(
                    vs, f"ЖК {projects[0]} {search_query}", k=8
                )
                # Добираем fallback тоже по этому ЖК
                fallback_results = _search_docs_fallback(
                    vs, f"ЖК {projects[0]} {search_query}", k=4
                )
                for doc in fallback_results:
                    if doc not in docs:
                        docs.append(doc)
            else:
                # Если ЖК вообще не назван (общий вопрос), ищем стандартно
                docs = _search_relevant_docs(vs, search_query, k=12)

    except Exception as e:
        print(f"Ошибка поиска в Qdrant: {e}")
        return None, None, None

    seen = set()
    unique_docs = []
    for doc in docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc)

    docs = unique_docs[:12]

    if not docs:
        return None, None, None

    context_parts = []
    for d in docs:
        source = d.metadata.get("source", "неизвестный источник")
        context_parts.append(f"[ИСТОЧНИК: {source}]\n{d.page_content}")

    context = "\n\n".join(context_parts)

    return context, projects, docs


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
