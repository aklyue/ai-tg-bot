import os
import tempfile
import asyncio
import aiohttp
from dotenv import load_dotenv
try:
    from aiohttp_socks import ProxyConnector
except ImportError:
    ProxyConnector = None

load_dotenv()

SONIOX_API_KEY = os.getenv("SONIOX_API_KEY")
SONIOX_API_BASE_URL = "https://api.soniox.com"
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")


async def transcribe_audio(file_url: str) -> str:
    """
    Асинхронная транскрибация голосового сообщения через Soniox async REST API.
    """
    if not SONIOX_API_KEY:
        print("ОШИБКА: SONIOX_API_KEY не указан")
        return ""

    headers = {"Authorization": f"Bearer {SONIOX_API_KEY}"}
    connector = None
    telegram_request_kwargs = {}
    if TELEGRAM_PROXY and TELEGRAM_PROXY.startswith(("socks4://", "socks5://")):
        if ProxyConnector is None:
            print("ОШИБКА: для SOCKS proxy установите aiohttp-socks")
            return ""
        connector = ProxyConnector.from_url(TELEGRAM_PROXY)
    elif TELEGRAM_PROXY:
        telegram_request_kwargs["proxy"] = TELEGRAM_PROXY
    
    try:
        # Скачиваем аудиофайл с Telegram
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=30), **telegram_request_kwargs) as audio_response:
                if audio_response.status != 200:
                    print(f"Ошибка скачивания аудио: HTTP {audio_response.status}")
                    return ""
                audio_content = await audio_response.read()

            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
                tmp.write(audio_content)
                tmp_path = tmp.name

            # 1. Загружаем файл
            print("Soniox: загрузка файла...")
            with open(tmp_path, "rb") as f:
                file_data = aiohttp.FormData()
                file_data.add_field('file', f, filename='audio.ogg')
                async with session.post(
                    f"{SONIOX_API_BASE_URL}/v1/files",
                    headers=headers,
                    data=file_data,
                ) as res:
                    if res.status not in (200, 201):
                        error_text = await res.text()
                        print(f"Soniox upload error: {res.status} - {error_text[:200]}")
                        os.unlink(tmp_path)
                        return ""
                    data = await res.json()
                    file_id = data["id"]
            print(f"Soniox: file_id = {file_id}")

            # 2. Создаем транскрипцию
            config = {
                "model": "stt-async-v5",
                "language_hints": ["ru"],
                "file_id": file_id,
            }
            async with session.post(
                f"{SONIOX_API_BASE_URL}/v1/transcriptions",
                headers=headers,
                json=config,
            ) as res:
                if res.status not in (200, 201):
                    error_text = await res.text()
                    print(f"Soniox create error: {res.status} - {error_text[:200]}")
                    async with session.delete(f"{SONIOX_API_BASE_URL}/v1/files/{file_id}", headers=headers):
                        pass
                    os.unlink(tmp_path)
                    return ""
                data = await res.json()
                transcription_id = data["id"]
            print(f"Soniox: transcription_id = {transcription_id}")

            # 3. Ждем завершения (асинхронно)
            while True:
                async with session.get(
                    f"{SONIOX_API_BASE_URL}/v1/transcriptions/{transcription_id}",
                    headers=headers,
                ) as res:
                    data = await res.json()
                
                if data["status"] == "completed":
                    break
                elif data["status"] == "error":
                    print(f"Ошибка Soniox: {data.get('error_message', 'Unknown')}")
                    break
                await asyncio.sleep(1)

            # 4. Получаем результат
            async with session.get(
                f"{SONIOX_API_BASE_URL}/v1/transcriptions/{transcription_id}/transcript",
                headers=headers,
            ) as res:
                result = await res.json()

            # 5. Очистка
            async with session.delete(f"{SONIOX_API_BASE_URL}/v1/transcriptions/{transcription_id}", headers=headers):
                pass
            async with session.delete(f"{SONIOX_API_BASE_URL}/v1/files/{file_id}", headers=headers):
                pass
            os.unlink(tmp_path)

            # Собираем текст из финальных токенов
            text = "".join(token["text"] for token in result.get("tokens", []))
            return text.strip() if text else ""

    except Exception as e:
        print(f"Ошибка при транскрибации: {e}")
        import traceback
        traceback.print_exc()
        return ""
