"""
API сервер для админки бота.
Предоставляет эндпоинты для управления базой знаний и просмотра статистики.
"""

import os
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uvicorn

from parser import sync_knowledge_base, parsing_log, KNOWLEDGE_SOURCES

# Импорты из bot
from bot.rag import list_sources, client, COLLECTION_NAME

app = FastAPI(title="Bot Admin API", version="1.0.0")

# CORS для frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Мок-данные для истории диалогов (в продакшене заменить на БД)
dialog_history: List[Dict[str, Any]] = []

# Мок-данные для статусов парсинга
parsing_statuses: Dict[str, Dict[str, Any]] = {}


class SourceInfo(BaseModel):
    id: int
    name: str
    url: str
    type: str
    lastParsed: str
    status: str


class DialogueInfo(BaseModel):
    id: int
    userId: int
    userName: str
    question: str
    answer: str
    timestamp: str


class KnowledgeItem(BaseModel):
    id: int
    source: str
    content: str
    chunk: str


class RefreshRequest(BaseModel):
    pass


@app.get("/api/sources", response_model=List[SourceInfo])
async def get_sources():
    """Получить список источников базы знаний с актуальным статусом"""
    # Собираем все URL из настроек парсера
    all_urls = KNOWLEDGE_SOURCES["websites"] + KNOWLEDGE_SOURCES["documents"]
    result = []
    
    for idx, url in enumerate(all_urls, 1):
        last_log = next((item for item in reversed(parsing_log) if item["source"] == url), None)
        
        result.append(SourceInfo(
            id=idx,
            name=url.split("/")[-1] or url,
            url=url,
            type="website" if url in KNOWLEDGE_SOURCES["websites"] else "document",
            lastParsed=last_log["timestamp"] if last_log else "Никогда",
            status=last_log["status"] if last_log else "unknown"
        ))
    return result


@app.get("/api/dialogues", response_model=List[DialogueInfo])
async def get_dialogues(limit: int = 50):
    """Получить историю диалогов"""
    # В продакшене загружать из БД
    return dialog_history[-limit:]


@app.get("/api/knowledge", response_model=List[KnowledgeItem])
async def get_knowledge(limit: int = 100):
    """Получить содержимое базы знаний"""
    if not client.collection_exists(COLLECTION_NAME):
        raise HTTPException(status_code=404, detail="База знаний пуста")
    
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    
    result = []
    for idx, point in enumerate(points, 1):
        payload = point.payload
        result.append(KnowledgeItem(
            id=idx,
            source=payload.get("metadata", {}).get("source", payload.get("source", "unknown")),
            content=payload.get("page_content", "")[:500],  # Ограничиваем длину
            chunk=payload.get("metadata", {}).get("type", "unknown")
        ))
    return result


@app.post("/api/refresh")
async def refresh_knowledge():
    # Запускаем через отдельный процесс или хотя бы через asyncio.create_task 
    # с обработкой ошибок внутри функции
    asyncio.create_task(sync_knowledge_base())
    return {"status": "started"}


@app.post("/api/dialogues", response_model=DialogueInfo)
async def add_dialogue(dialogue: DialogueInfo):
    """Добавить диалог в историю"""
    dialog_history.append(dialogue.model_dump())
    return dialogue


@app.get("/api/stats")
async def get_stats():
    """Получить статистику"""
    if not client.collection_exists(COLLECTION_NAME):
        return {
            "sources_count": 0,
            "documents_count": 0,
            "dialogues_count": len(dialog_history)
        }
    
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )
    
    sources = set()
    for point in points:
        if point.payload:
            source = point.payload.get("metadata", {}).get("source", point.payload.get("source"))
            if source:
                sources.add(source)
    
    return {
        "sources_count": len(sources),
        "documents_count": len(points),
        "dialogues_count": len(dialog_history)
    }


def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Запустить API сервер"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()