from qdrant_client import QdrantClient
import json

URL = "https://a9382634-7467-4ba9-9930-3eb13945b2b4.us-west-2-0.aws.cloud.qdrant.io"
COLLECTION = "knowledge_base"
# ВСТАВЬ СЮДА СВОЙ КЛЮЧ ИЗ .ENV ФАЙЛА
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MGQ0NTA5NTAtNGRlOC00Mjg1LTg2OGMtYmVhZTA5OGZhNTdlIn0.Uk8ZZwOWIlPhkoCUi9ZyKLEDnRPI2in30HGcRbhe1fY" 

client = QdrantClient(
    url=URL,
    api_key=API_KEY
)


offset = None

while True:
    records, offset = client.scroll(
        collection_name=COLLECTION,
        limit=100,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )

    for rec in records:
        payload = rec.payload

        source = payload.get("metadata", {}).get("source", "")

        if "1eoDdo42FXrV6unkQhlmaOMQFupOpdnRFjM7_oZDP9XU" in source:
            print("=" * 80)
            print("НАШЕЛ ДОКУМЕНТ")
            print(payload)
            print("=" * 80)

    if offset is None:
        break