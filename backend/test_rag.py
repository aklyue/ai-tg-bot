import sys
sys.path.insert(0, '.')
import os
os.chdir('.')

from bot.rag import get_answer, get_answer_stream
import asyncio
import time

test_queries = [
    ("Сравни ипотеку в ЖК Алиса и ЖК Бестселлер", []),
    ("Расскажи о ЖК Алиса и ЖК Бестселлер", []),
    ("Какая ипотека в ЖК Алиса?", []),
    ("Какая ипотеку в ЖК Бестселлер?", []),
    ("Расскажи о ЖК Алиса", []),
    ("Расскажи о ЖК Бестселлер", []),
]

async def test_sync():
    """Тест синхронного ответа"""
    for q, history in test_queries:
        start = time.time()
        answer = await get_answer(q, history=history)
        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"ВОПРОС: {q}")
        print(f"ИСТОРИЯ: {len(history)} сообщений")
        print(f"ВРЕМЯ: {elapsed:.1f}с")
        print(f"ОТВЕТ:\n{answer}")
        print(f"{'='*60}")

async def test_stream():
    """Тест streaming ответа"""
    for q, history in test_queries[:2]:
        start = time.time()
        print(f"\n{'='*60}")
        print(f"ВОПРОС: {q}")
        print(f"СТРИМИНГ:")
        full_text = ""
        async for chunk in get_answer_stream(q, history):
            full_text += chunk
            print(chunk, end="", flush=True)
        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"ВРЕМЯ: {elapsed:.1f}с")

if __name__ == "__main__":
    print("=== Тест синхронного режима ===")
    asyncio.run(test_sync())
    print("\n\n=== Тест streaming режима ===")
    asyncio.run(test_stream())
