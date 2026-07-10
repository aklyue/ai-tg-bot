import sys
sys.path.insert(0, '.')
from bot.rag import list_sources, client, COLLECTION_NAME

# Проверяем источники
sources = list_sources()
print('Sources in Qdrant:')
for s in sources:
    print(f'  - {s}')

# Проверяем количество точек
points, _ = client.scroll(collection_name=COLLECTION_NAME, limit=1000, with_payload=False, with_vectors=False)
print(f'\nTotal points: {len(points)}')

# Проверяем источники с payload
points, _ = client.scroll(collection_name=COLLECTION_NAME, limit=1000, with_payload=True, with_vectors=False)
sources_with_payload = set()
for p in points:
    source = p.payload.get("metadata", {}).get("source", p.payload.get("source", "unknown"))
    sources_with_payload.add(source)

print('\nSources with payload:')
for s in sorted(sources_with_payload):
    print(f'  - {s}')