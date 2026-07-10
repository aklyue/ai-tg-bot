import asyncio
import os
import aiohttp
from datetime import datetime
from playwright.async_api import async_playwright
from bot.rag import add_documents_to_db, ensure_collection_exists
import tempfile
import zipfile
from io import BytesIO
from urllib.parse import quote
import xml.etree.ElementTree as ET

SOURCES_META = {
    "https://best.baza.bz": {"name": "ЖК Бестселлер (Москва)", "type": "website"},
    "https://alisa.baza.bz": {"name": "ЖК Алиса (Екатеринбург)", "type": "website"},
    "https://docs.google.com/document/d/1eoDdo42FXrV6unkQhlmaOMQFupOpdnRFjM7_oZDP9XU/edit": {"name": "ЖК Бестселлер — Инструменты продаж", "type": "document"},
    "https://docs.google.com/spreadsheets/d/1p1DZQPIQC4cc2V4K3Z3M4RaIrU6L9NjVd2tbvJXXPls/edit": {"name": "ЖК Алиса — База знаний", "type": "document"},
    "https://docs.google.com/document/d/16m4dXLBi8sSEiquaUvO2tZycpiFVOUfsXl-QdIsKDpE/edit": {"name": "Инструменты продаж 2 волны (Алиса/ДМД)", "type": "document"},
    "https://cloud.baza.bz/index.php/apps/files/files/2351865?dir=/ЖК/Бестселлер/умный%20дом&editing=false&openfile=true": {"name": "ЖК Бестселлер — умная квартира и умный дом", "type": "document"},
    "https://cloud.baza.bz/index.php/apps/files/files/2508899?dir=/ЖК/Бестселлер/презентации/финальная%20презентация": {"name": "ЖК Бестселлер — общая презентация проекта", "type": "document"},
    "https://disk.yandex.ru/d/BXqSX-BtE_IT2g": {"name": "Все презентации проектов", "type": "document"},
}

KNOWLEDGE_SOURCES = {
    "websites": [
        "https://best.baza.bz",
        "https://alisa.baza.bz",
    ],
    "documents": [
        "https://docs.google.com/document/d/1eoDdo42FXrV6unkQhlmaOMQFupOpdnRFjM7_oZDP9XU/edit",
        "https://docs.google.com/spreadsheets/d/1p1DZQPIQC4cc2V4K3Z3M4RaIrU6L9NjVd2tbvJXXPls/edit",
        "https://docs.google.com/document/d/16m4dXLBi8sSEiquaUvO2tZycpiFVOUfsXl-QdIsKDpE/edit",
        "https://cloud.baza.bz/index.php/apps/files/files/2351865?dir=/ЖК/Бестселлер/умный%20дом&editing=false&openfile=true",
        "https://cloud.baza.bz/index.php/apps/files/files/2508899?dir=/ЖК/Бестселлер/презентации/финальная%20презентация",
        "https://disk.yandex.ru/d/BXqSX-BtE_IT2g",
    ]
}

parsing_log = []


def log_parsing(source: str, status: str, message: str):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "status": status,
        "message": message
    }
    parsing_log.append(entry)
    print(f"[{status}] {source}: {message}")


def extract_ooxml_text(content: bytes, suffix: str) -> str:
    """Извлечь текст из DOCX/PPTX без дополнительных зависимостей."""
    text_parts = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        if suffix == ".docx":
            names = [name for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
        elif suffix == ".pptx":
            names = [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
        else:
            return ""

        for name in sorted(names):
            try:
                root = ET.fromstring(archive.read(name))
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        text_parts.append(node.text)
            except Exception:
                continue

    return "\n".join(text_parts)


def extract_zip_text(content: bytes) -> str:
    """Извлечь текст из архива с txt/csv/docx/pptx/pdf файлами."""
    text_parts = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        for name in archive.namelist():
            lower = name.lower()
            if name.endswith("/"):
                continue
            try:
                file_content = archive.read(name)
                if lower.endswith((".txt", ".csv", ".md")):
                    text_parts.append(file_content.decode("utf-8", errors="ignore"))
                elif lower.endswith(".docx"):
                    text_parts.append(extract_ooxml_text(file_content, ".docx"))
                elif lower.endswith(".pptx"):
                    text_parts.append(extract_ooxml_text(file_content, ".pptx"))
                elif lower.endswith(".pdf"):
                    from pypdf import PdfReader
                    reader = PdfReader(BytesIO(file_content))
                    text_parts.append("\n".join(page.extract_text() or "" for page in reader.pages))
            except Exception as e:
                text_parts.append(f"\n[Не удалось прочитать {name}: {e}]\n")

    return "\n\n".join(part for part in text_parts if part.strip())


async def parse_website(url: str):
    """Парсинг сайта через Playwright с обходом защиты от ботов"""
    meta = SOURCES_META.get(url, {"name": url, "type": "website"})
    log_parsing(url, "INFO", f"Начало процесса парсинга: {meta['name']}")
    try:
        async with async_playwright() as p:
            chromium_path = os.getenv("PLAYWRIGHT_CHROMIUM_PATH")
            launch_kwargs = {
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            }
            
            if chromium_path:
                launch_kwargs["executable_path"] = chromium_path
                
            log_parsing(url, "INFO", "Запуск браузера...")
            browser = await p.chromium.launch(**launch_kwargs)
            
            # Создаем контекст с более реалистичными настройками
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                permissions=["geolocation"],
                geolocation={"latitude": 55.7558, "longitude": 37.6173}
            )
            page = await context.new_page()
            
            # Добавляем скрипт для скрытия автоматизации
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en'] });
            """)
            
            # Устанавливаем заголовки
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            })
            
            log_parsing(url, "INFO", f"Переход на главную: {url}")
            # Устанавливаем большой таймаут для SPA
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            
            # Ждём полной загрузки контента
            await page.wait_for_timeout(5000)
            
            log_parsing(url, "INFO", "Скроллинг для подгрузки контента...")
            # Скроллим для загрузки ленивого контента
            for i in range(5):
                await page.evaluate(f"window.scrollTo(0, {(i + 1) * 300})")
                await page.wait_for_timeout(1000)
            
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            # Пробуем разные способы получить контент
            content = ""
            log_parsing(url, "INFO", "Извлечение текстового контента...")
            
            # Способ 1: innerText
            try:
                content = await page.evaluate("document.body.innerText")
            except:
                pass
            
            # Способ 2: textContent
            if len(content) < 500:
                try:
                    content = await page.evaluate("document.body.textContent")
                except:
                    pass
            
            # Способ 3: Все текстовые ноды
            if len(content) < 500:
                try:
                    content = await page.evaluate("""
                        Array.from(document.body.querySelectorAll('*'))
                            .map(el => el.textContent)
                            .join('\\n')
                    """)
                except:
                    pass
            
            # Fallback: aiohttp + BeautifulSoup
            if len(content) < 1000:
                try:
                    from bs4 import BeautifulSoup
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }) as response:
                            if response.status == 200:
                                html = await response.text()
                                soup = BeautifulSoup(html, 'html.parser')
                                for script in soup(["script", "style"]):
                                    script.decompose()
                                fallback_content = soup.get_text(separator='\n', strip=True)
                                if len(fallback_content) > len(content):
                                    content = fallback_content
                                    log_parsing(url, "INFO", f"Fallback BeautifulSoup: {len(content)} символов")
                except ImportError:
                    log_parsing(url, "WARNING", "Установите beautifulsoup4")
                except Exception as e:
                    log_parsing(url, "WARNING", f"Fallback ошибка: {e}")

            # Собираем внутренние ссылки
            try:
                log_parsing(url, "INFO", "Поиск внутренних ссылок...")
                all_links = await page.eval_on_selector_all(
                    "a[href]",
                    "elements => elements.map(el => el.href)"
                )
            except:
                all_links = []

            base_domain = url.rstrip("/").split("//")[1] if "//" in url else url
            internal_pages = set()
            log_parsing(url, "INFO", f"Найдено {len(internal_pages)} внутренних ссылок. Парсим первые 10...")
            for link in all_links:
                if base_domain in link and not link.endswith((".pdf", ".zip", ".jpg", ".png", "#")):
                    if link not in internal_pages:
                        internal_pages.add(link)

            # Парсим внутренние страницы
            for link in list(internal_pages)[:10]:
                try:
                    log_parsing(url, "INFO", f"[{i+1}/10] Парсинг ссылки: {link}")
                    await page.goto(link, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    for i in range(3):
                        await page.evaluate(f"window.scrollTo(0, {(i + 1) * 500})")
                        await page.wait_for_timeout(1000)
                    page_content = await page.evaluate("document.body.innerText")
                    content += f"\n\n=== {link} ===\n\n" + page_content
                except Exception as e:
                    log_parsing(url, "WARNING", f"Ошибка при парсинге {link}: {e}")

            await browser.close()
            log_parsing(url, "INFO", "Браузер закрыт.")

            enriched = f"Информация о {meta['name']}. Сайт: {url}\n\n{content}"
            log_parsing(url, "INFO", "Отправка данных в базу знаний...")
            await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "website"})
            log_parsing(url, "SUCCESS", f"{meta['name']}: {len(content)} символов, {len(internal_pages)} страниц")
            return True
    except Exception as e:
        log_parsing(url, "ERROR", f"{meta['name']}: {e}")
        return False


async def parse_document(url: str):
    """Парсинг документа (асинхронный)"""
    meta = SOURCES_META.get(url, {"name": url, "type": "document"})
    try:
        if "disk.yandex.ru" in url:
            # Используем Yandex Disk API для получения информации о папке/файле
            public_key = quote(url, safe="")
            api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_key}&limit=100"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        log_parsing(url, "ERROR", f"Yandex Disk API HTTP {response.status}")
                        return False
                    data = await response.json()
                    
                text_parts = []
                
                # Если это папка, скачиваем файлы из неё
                if "_embedded" in data and "items" in data["_embedded"]:
                    items = data["_embedded"]["items"]
                    for item in items[:20]:  # Ограничиваем количество файлов
                        if item.get("type") == "file":
                            file_name = item.get("name", "")
                            file_url = item.get("file", "")
                            if file_url:
                                try:
                                    async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=60)) as file_response:
                                        if file_response.status == 200:
                                            file_content = await file_response.read()
                                            if file_name.endswith(('.txt', '.csv', '.md')):
                                                text_parts.append(f"=== {file_name} ===\n{file_content.decode('utf-8', errors='ignore')}")
                                            elif file_name.endswith('.pdf'):
                                                from pypdf import PdfReader
                                                reader = PdfReader(BytesIO(file_content))
                                                file_text = "\n".join(page.extract_text() or "" for page in reader.pages)
                                                text_parts.append(f"=== {file_name} ===\n{file_text}")
                                except Exception as e:
                                    log_parsing(url, "WARNING", f"Ошибка чтения {file_name}: {e}")
                
                text = "\n\n".join(text_parts) if text_parts else data.get("name", "Yandex Disk")
                enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов, {len(text_parts)} файлов")
                return True

        if "docs.google.com" in url:
            if "/document/" in url:
                doc_id = url.split("/d/")[1].split("/")[0]
                export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            elif "/spreadsheets/" in url:
                doc_id = url.split("/d/")[1].split("/")[0]
                export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
            else:
                log_parsing(url, "ERROR", "Неизвестный тип Google Docs")
                return False

            async with aiohttp.ClientSession() as session:
                async with session.get(export_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        text = await response.text()
                        enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                        await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                        log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов")
                        return True
                    else:
                        log_parsing(url, "ERROR", f"HTTP {response.status}")
                        return False

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    log_parsing(url, "ERROR", f"HTTP {response.status}")
                    return False

                content_type = response.headers.get("content-type", "")
                lower_url = str(response.url).lower()
                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    content = await response.read()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name

                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(tmp_path)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                        await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                        log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов")
                    except ImportError:
                        log_parsing(url, "WARNING", "Установите pypdf")
                    finally:
                        os.unlink(tmp_path)
                    return True
                elif "zip" in content_type or lower_url.endswith(".zip"):
                    content = await response.read()
                    text = extract_zip_text(content)
                    enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                    await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                    log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов")
                    return True
                elif lower_url.endswith(".docx"):
                    content = await response.read()
                    text = extract_ooxml_text(content, ".docx")
                    enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                    await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                    log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов")
                    return True
                elif lower_url.endswith(".pptx"):
                    content = await response.read()
                    text = extract_ooxml_text(content, ".pptx")
                    enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                    await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                    log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов")
                    return True
                else:
                    text = await response.text()
                    enriched = f"Информация из документа: {meta['name']}. Ссылка: {url}\n\n{text}"
                    await asyncio.to_thread(add_documents_to_db, enriched, {"source": url, "type": "document"})
                    log_parsing(url, "SUCCESS", f"{meta['name']}: {len(text)} символов")
                    return True
    except Exception as e:
        log_parsing(url, "ERROR", f"{meta['name']}: {e}")
        return False



async def sync_knowledge_base():
    print("=" * 50)
    print("Начинаем обновление базы знаний...")
    print("=" * 50)

    # УБРАТЬ: clear_collection() <-- Эту строку удалить!
    
    # Сначала создаем один раз, чтобы избежать гонки
    ensure_collection_exists()

    for url in KNOWLEDGE_SOURCES["documents"]:
        await parse_document(url)
        
    for url in KNOWLEDGE_SOURCES["websites"]:
        await parse_website(url)

    print("=" * 50)
    success_count = sum(1 for e in parsing_log if e["status"] == "SUCCESS")
    error_count = sum(1 for e in parsing_log if e["status"] == "ERROR")
    print(f"Готово. Успешно: {success_count}, Ошибок: {error_count}")
    print("=" * 50)

    print("\nЛог:")
    for entry in parsing_log:
        print(f"  [{entry['status']}] {entry['source']}: {entry['message']}")


if __name__ == "__main__":
    asyncio.run(sync_knowledge_base())
