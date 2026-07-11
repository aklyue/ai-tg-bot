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


records, _ = client.scroll(
    collection_name=COLLECTION,
    limit=3,
    with_payload=True,
    with_vectors=False,
)


for i, rec in enumerate(records):

    print("\n" + "=" * 80)
    print(f"ЗАПИСЬ {i + 1}")
    print("=" * 80)

    print("ID:")
    print(rec.id)

    print("\nPAYLOAD:")
    print(json.dumps(
        rec.payload,
        indent=4,
        ensure_ascii=False
    ))

    print("\nКЛЮЧИ PAYLOAD:")
    print(list(rec.payload.keys()))