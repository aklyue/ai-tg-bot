from qdrant_client.models import PayloadSchemaType
from bot.rag import client, COLLECTION_NAME


client.create_payload_index(
    collection_name="knowledge_base",
    field_name="metadata.project",
    field_schema={
        "type": "keyword"
    }
)

print("Индекс project создан")