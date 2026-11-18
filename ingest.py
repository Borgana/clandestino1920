#!/usr/bin/env python3
"""
Ingesta Knowledge Base Clandestino 1920 → Qdrant Cloud
Ejecuta: python ingest.py
"""

import os
import json
import hashlib
from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm

# ─── LEE .ENV NATIVAMENTE (sin python-dotenv) ────────────────────────────
ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

# ─── CONFIG ──────────────────────────────────────────────────────────────
COLLECTION = "clandestino_kb"
DATA_DIR = Path("data")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dim, CPU, multilingüe
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
BATCH_SIZE = 100

if not QDRANT_URL or not QDRANT_API_KEY:
    raise RuntimeError(
        "Faltan QDRANT_URL / QDRANT_API_KEY en .env\n"
        f"Revisa {ENV_PATH.resolve()}"
    )

# ─── CLIENTES ────────────────────────────────────────────────────────────
model = SentenceTransformer(EMBED_MODEL)
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# ─── UTILIDADES ──────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Trocea texto largo en chunks con solape."""
    if len(text) <= size:
        return [text]
    chunks = []
    for i in range(0, len(text), size - overlap):
        chunks.append(text[i:i + size])
    return chunks

def make_id(*parts: str) -> int:
    """ID determinístico a partir de strings (hash 64 bits → int)."""
    h = hashlib.md5("|".join(parts).encode()).hexdigest()
    return int(h[:16], 16)  # 64 bits = cabe en uint64 de Qdrant

def upsert_batch(points: list[PointStruct]):
    """Sube lote a Qdrant con reintentos simples."""
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION, points=batch, wait=True)

# ─── PROCESADORES POR TIPO DE ARCHIVO ────────────────────────────────────

def process_carta(json_path: Path) -> list[PointStruct]:
    """Procesa carta.json → un punto por ítem (cóctel, destilado, cerveza...)."""
    items = json.loads(json_path.read_text(encoding="utf-8"))
    points = []
    for item in tqdm(items, desc="Procesando carta"):
        text_parts = [
            f"Nombre: {item['nombre']}",
            f"Categoría: {item['categoria']} > {item.get('subcategoria', '')}",
            f"Precio: {item['precio']}€" if item['precio'] else "Precio: consultar",
            f"Descripción: {item['descripcion']}",
        ]
        if item.get("ingredientes"):
            text_parts.append(f"Ingredientes: {', '.join(item['ingredientes'])}")
        if item.get("alergenos"):
            text_parts.append(f"Alérgenos: {', '.join(item['alergenos'])}")
        full_text = "\n".join(text_parts)

        payload = {
            "text": full_text,
            "source": "carta",
            "tipo": "item",
            "nombre": item["nombre"],
            "categoria": item["categoria"],
            "subcategoria": item.get("subcategoria", ""),
            "precio": item["precio"],
            "alergenos": item.get("alergenos", []),
            "ingredientes": item.get("ingredientes", []),
        }

        vector = model.encode(full_text).tolist()
        points.append(PointStruct(
            id=make_id("carta", item["nombre"]),
            vector=vector,
            payload=payload
        ))
    return points


def process_markdown(md_path: Path, doc_type: str) -> list[PointStruct]:
    """Procesa .md (lore, tecnicas, alergenos, eventos) → chunks con metadata."""
    text = md_path.read_text(encoding="utf-8")
    chunks = chunk_text(text)
    points = []
    for i, chunk in enumerate(tqdm(chunks, desc=f"Procesando {md_path.name}")):
        payload = {
            "text": chunk,
            "source": md_path.stem,
            "tipo": doc_type,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        vector = model.encode(chunk).tolist()
        points.append(PointStruct(
            id=make_id(md_path.stem, str(i)),
            vector=vector,
            payload=payload
        ))
    return points


# ─── MAIN ────────────────────────────────────────────────────────────────

def main():
    print(f"🔗 Conectando a Qdrant: {QDRANT_URL}")
    print(f"📦 Colección: {COLLECTION}")

    if not client.collection_exists(COLLECTION):
        print("🆕 Creando colección...")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    else:
        print("✅ Colección ya existe")

    all_points = []

    # 1. Carta (JSON estructurado)
    carta_path = DATA_DIR / "carta.json"
    if carta_path.exists():
        all_points.extend(process_carta(carta_path))
    else:
        print(f"⚠️  No existe {carta_path}")

    # 2. Archivos markdown
    md_configs = [
        ("lore.md", "lore"),
        ("tecnicas.md", "tecnica"),
        ("alergenos.md", "alergenos"),
        ("eventos.md", "eventos"),
        ("tono.md", "tono"),
    ]
    for fname, dtype in md_configs:
        fpath = DATA_DIR / fname
        if fpath.exists():
            all_points.extend(process_markdown(fpath, dtype))
        else:
            print(f"⚠️  No existe {fpath} (se omite)")

    if not all_points:
        print("❌ No hay puntos para indexar. Revisa data/")
        return

    print(f"\n📤 Subiendo {len(all_points)} puntos a Qdrant...")
    upsert_batch(all_points)

    count = client.count(collection_name=COLLECTION, exact=True).count
    print(f"\n✅ INGESTA COMPLETA — {count} vectores en '{COLLECTION}'")

    # Test rápido
    test_query = "Old Fashioned whisky azucar angostura"
    test_vec = model.encode(test_query).tolist()
    results = client.search(
        collection_name=COLLECTION,
        query_vector=test_vec,
        limit=3,
        with_payload=True
    )
    print("\n🔍 Test búsqueda 'Old Fashioned':")
    for r in results:
        print(f"  [{r.score:.3f}] {r.payload.get('nombre') or r.payload.get('source')} — {r.payload['text'][:120]}...")


if __name__ == "__main__":
    main()