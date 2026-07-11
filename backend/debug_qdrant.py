from qdrant_client import QdrantClient

URL = "https://a9382634-7467-4ba9-9930-3eb13945b2b4.us-west-2-0.aws.cloud.qdrant.io"
COLLECTION = "knowledge_base"
# ВСТАВЬ СЮДА СВОЙ КЛЮЧ ИЗ .ENV ФАЙЛА
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MGQ0NTA5NTAtNGRlOC00Mjg1LTg2OGMtYmVhZTA5OGZhNTdlIn0.Uk8ZZwOWIlPhkoCUi9ZyKLEDnRPI2in30HGcRbhe1fY" 

client = QdrantClient(url=URL, api_key=API_KEY)

# Добавляем фильтр по скроллу не нужен, просто выгружаем
records, _ = client.scroll(
    collection_name=COLLECTION,
    limit=3,
    with_payload=True
)

for i, rec in enumerate(records):
    print(f"\n--- ЗАПИСЬ {i+1} ---")
    print(f"PAYLOAD: {rec.payload}")