import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError
from bot.rag import get_answer, get_answer_stream
from bot.stt import transcribe_audio
import os
from datetime import datetime
from aiohttp import web

from dotenv import load_dotenv

load_dotenv()

proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
if proxy:
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy

TOKEN = os.environ["TG_BOT_TOKEN"]
TELEGRAM_PROXY = (
    os.getenv("TELEGRAM_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
)
API_BASE_URL = os.getenv("API_BASE_URL", "https://ai-tg-bot-bqlk.onrender.com")

bot_kwargs = {"default": DefaultBotProperties(parse_mode="HTML")}
if TELEGRAM_PROXY:
    bot_kwargs["session"] = AiohttpSession(proxy=TELEGRAM_PROXY)

bot = Bot(token=TOKEN, **bot_kwargs)
dp = Dispatcher()

async def health_check(request):
    return web.Response(text="Bot is running")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', health_check)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

# Хранилище истории диалогов (в продакшене заменить на БД)
# user_id -> [(role, text), ...]
dialogues = {}


def get_history(user_id: int):
    """Получить историю диалога пользователя"""
    return dialogues.get(user_id, [])


def add_to_history(user_id: int, role: str, text: str):
    """Добавить сообщение в историю"""
    if user_id not in dialogues:
        dialogues[user_id] = []
    dialogues[user_id].append((role, text))
    # Держим последние 20 сообщений
    if len(dialogues[user_id]) > 20:
        dialogues[user_id] = dialogues[user_id][-20:]


async def save_dialogue_to_api(
    user_id: int, user_name: str, question: str, answer: str
):
    """Сохранить диалог в API"""
    try:
        logging.info(f"Saving dialogue to API: {user_name} - {question[:50]}...")

        # Генерируем временный id (например, на основе timestamp)
        # или передаем 0, если ваш API сам перезаписывает id в бэкенде
        dummy_id = int(datetime.now().timestamp())

        payload = {
            "id": dummy_id,
            "userId": user_id,
            "userName": user_name,
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/api/dialogues",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:

                # Проверяем реальный HTTP-статус ответа сервера
                if response.status == 200:
                    logging.info("Dialogue saved successfully")
                else:
                    error_text = await response.text()
                    logging.error(
                        f"API rejected request with status {response.status}: {error_text}"
                    )

    except Exception as e:
        logging.error(f"Failed to save dialogue to API due to network/code error: {e}")


async def stream_answer(message: types.Message, query: str, history: list):
    """Стриминг ответа от LLM с настоящим streaming"""
    logging.info("DEBUG: stream_answer - Начало")

    # Отправляем начальное сообщение
    msg = await message.answer("⏳ Думаю...")
    logging.info("DEBUG: stream_answer - Сообщение 'Думаю' отправлено")

    full_text = ""
    last_update_len = 0
    update_interval = 200

    try:
        async for chunk in get_answer_stream(query, history):
            full_text += chunk

            # Обновляем сообщение реже
            if len(full_text) - last_update_len >= update_interval:
                try:
                    await bot.edit_message_text(
                        full_text + "▌",
                        chat_id=msg.chat.id,
                        message_id=msg.message_id,
                    )
                    last_update_len = len(full_text)
                except Exception as e:
                    logging.warning(f"DEBUG: Ошибка обновления стриминга: {e}")
                    pass

        logging.info(
            f"DEBUG: stream_answer - Цикл завершен. Длина ответа: {len(full_text)}"
        )

    except Exception as e:
        logging.error(
            f"DEBUG: !!! КРИТИЧЕСКАЯ ОШИБКА ВНУТРИ ЦИКЛА STREAM_ANSWER: {e}",
            exc_info=True,
        )
        raise  # Пробрасываем ошибку дальше, чтобы handle_text знал, что стриминг упал

    # Финальное обновление
    try:
        logging.info("DEBUG: stream_answer - Финальное обновление")
        await bot.edit_message_text(
            full_text,
            chat_id=msg.chat.id,
            message_id=msg.message_id,
        )
    except Exception as e:
        logging.error(f"DEBUG: Ошибка финального обновления: {e}")
        pass

    logging.info("DEBUG: stream_answer - Успешное завершение")
    return full_text


@dp.message(F.voice)
async def handle_voice(message: types.Voice):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name or "unknown"
    try:
        file = await bot.get_file(message.voice.file_id)
        telegram_file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

        # Теперь transcribe_audio асинхронная функция
        text = await transcribe_audio(telegram_file_url)
        if not text:
            await message.answer(
                "Не удалось распознать голосовое сообщение. Попробуйте ещё раз или напишите текст."
            )
            return

        add_to_history(user_id, "user", text)
        history = get_history(user_id)
        answer = await stream_answer(message, text, history)
        add_to_history(user_id, "assistant", answer)

        # Сохраняем диалог в API
        await save_dialogue_to_api(user_id, f"@{user_name}", text, answer)

    except Exception as e:
        logging.error(f"Error processing voice: {e}")
        await message.answer(
            "Произошла ошибка при обработке голосового сообщения. Пожалуйста, свяжитесь с менеджером."
        )


@dp.message(F.text, F.text.startswith("/start"))
async def handle_start(message: types.Message):
    user_id = message.from_user.id
    dialogues[user_id] = []  # Очищаем историю
    await message.answer(
        "👋 Здравствуйте! Я — ассистент агента по недвижимости.\n\n"
        "Я могу помочь с вопросами по:\n"
        "• ЖК Бестселлер (Москва)\n"
        "• ЖК Алиса (Екатеринбург)\n"
        "• Вознаграждениям агентов\n"
        "• Финансовым инструментам (ипотека, рассрочка)\n"
        "• Контактам с менеджером\n\n"
        "Просто напишите свой вопрос или отправьте голосовое сообщение."
    )


@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name or "unknown"
    text = message.text

    logging.info(f"DEBUG: Начало обработки сообщения от {user_id}")

    add_to_history(user_id, "user", text)
    history = get_history(user_id)

    answer = None
    try:
        logging.info("DEBUG: Вызов stream_answer")
        answer = await stream_answer(message, text, history)
        add_to_history(user_id, "assistant", answer)
        logging.info("DEBUG: stream_answer завершен успешно")
    except Exception as e:
        logging.error(
            f"DEBUG: !!! КРИТИЧЕСКАЯ ОШИБКА В STREAM_ANSWER: {e}", exc_info=True
        )
        await message.answer("Ошибка при генерации ответа.")
        return

    try:
        logging.info(f"DEBUG: Вызов save_dialogue_to_api для {user_id}")
        await save_dialogue_to_api(user_id, f"@{user_name}", text, answer)
        logging.info("DEBUG: Сохранение успешно")
    except Exception as e:
        logging.error(f"DEBUG: !!! ОШИБКА ПРИ ВЫЗОВЕ API: {e}", exc_info=True)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if TELEGRAM_PROXY:
        logging.info(f"Telegram proxy configured: {TELEGRAM_PROXY}")
    else:
        logging.warning(
            "⚠️ TELEGRAM_PROXY not configured! "
            "If Telegram is blocked in your region, the bot will not be able to connect. "
            "Set TELEGRAM_PROXY in .env file (e.g., http://127.0.0.1:7890 or socks5://proxy:1080)"
        )

    connection_attempts = 0
    max_attempts_without_proxy = 3

    while True:
        try:
            print("Бот запущен...")
            await dp.start_polling(bot)
        except TelegramNetworkError as e:
            connection_attempts += 1
            error_msg = str(e)

            # Check if it's a connection error to api.telegram.org
            if "api.telegram.org" in error_msg or "Cannot connect to host" in error_msg:
                if (
                    not TELEGRAM_PROXY
                    and connection_attempts >= max_attempts_without_proxy
                ):
                    logging.error(
                        "❌ CRITICAL: Cannot connect to Telegram API after %d attempts.\n"
                        "   Telegram may be blocked in your region.\n"
                        "   SOLUTION: Configure TELEGRAM_PROXY in .env file:\n"
                        "   - If you have a VPN with proxy: http://127.0.0.1:7890\n"
                        "   - SOCKS5 proxy: socks5://proxy-server:1080\n"
                        "   - HTTP proxy: http://proxy-server:8080\n"
                        "   After setting the proxy, restart the bot.",
                        connection_attempts,
                    )
                    # Increase retry delay significantly if no proxy
                    await asyncio.sleep(60)
                else:
                    logging.error(
                        "Telegram network error: %s. Retry in 10 seconds... "
                        "If this persists, configure TELEGRAM_PROXY in .env",
                        error_msg,
                    )
                    await asyncio.sleep(10)
            else:
                logging.error(
                    f"Telegram network error: {error_msg}. Retry in 10 seconds..."
                )
                await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"Unexpected error: {type(e).__name__}: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
