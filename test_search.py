from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from pathlib import Path
import os

# Lee .env
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])

queries = [
    "cóctel sin alcohol para embarazada",
    "whisky japonés premium",
    "evento día mundial whisky",
    "alergenos huevo en cócteles",
    "técnica stirred vs shaken",
    "Old Fashioned Clandestino",
]

for q in queries:
    vec = model.encode(q).tolist()
    res = client.query_points(
        collection_name="clandestino_kb",
        query=vec,
        limit=2,
        with_payload=True
    ).points
    print(f"\n🔎 '{q}'")
    for r in res:
        src = r.payload.get('nombre') or r.payload.get('source', '?')
        print(f"  [{r.score:.3f}] {src} → {r.payload['text'][:150]}...")
