#!/usr/bin/env python3
"""
Creative Agent Clandestino 1920
Genera contenido para Instagram/Facebook usando Knowledge Base + LLM
Uso: python creative_agent.py "Old Fashioned" reel vender
"""

import os
import json
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from groq import Groq

# ─── CONFIG ──────────────────────────────────────────────────────────────

COLLECTION = "clandestino_kb"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "openai/gpt-oss-20b"  # Groq: rápido, gratis, 8K ctx

# ─── CARGA .ENV NATIVO ───────────────────────────────────────────────────

ENV_PATH = Path(".env")
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not all([QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY]):
    raise RuntimeError("Faltan QDRANT_URL, QDRANT_API_KEY o GROQ_API_KEY en .env")

# ─── CLIENTES ────────────────────────────────────────────────────────────

embed_model = SentenceTransformer(EMBED_MODEL)
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
groq = Groq(api_key=GROQ_API_KEY)

# ─── ESTRUCTURA DE SALIDA ────────────────────────────────────────────────

@dataclass
class CreativeOutput:
    copy: str
    shots_list: list[str]
    hashtags: list[str]
    alt_text: str
    citations: list[str]  # IDs de documentos usados

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)

# ─── PROMPT TEMPLATE ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres el Community Manager de **Clandestino 1920**, un speakeasy en Salamanca inspirado en la Ley Seca (1920s).
Tu voz: misteriosa, elegante, cómplice. "Nosotros" (el bar), "vosotros" (la clientela).
Vocabulario clave: secreto, misterio, curiosos, conquista, guardianes, ritual, ceremonia, esencia, alma.
Cada cóctel tiene historia real + toque de leyenda local.
CTAs suaves: "Venid a descubrir", "¿Te atreves?", "Enlace en bio", "Etiquetadnos".
Hashtags fijos: #clandestino1920 #salamanca #speakeasy #cocteleria + específicos.
Emojis estratégicos: 🕵🏼 🥃 ☕ ✨ 🖤 🔑 🚪 🌊 🐒 (pocos, con intención).
Longitud: 2-4 párrafos cortos, aireados, legibles en móvil.

FORMATOS:
- REEL: Hook 3s → desarrollo → CTA final. Incluye shots_list (lista de planos visuales).
- STORY: Interactivo (quiz, poll, pregunta). Texto en imagen + sticker sugerido.
- POST: Carousel o foto única. Copy + hashtags + alt_text.
- BLOG: SEO, estructura H2, 800-1200 palabras, schema FAQ.

REGLAS DE ORO:
1. SOLO usa información del CONTEXTO proporcionado (carta, lore, técnicas, alérgenos, eventos).
2. Si el contexto no tiene la info → "No está en nuestra carta" / "Preguntad en barra".
3. Cita siempre los IDs de documentos usados en 'citations'.
4. Alérgenos: si el cóctel los tiene, menciónalos sutilmente.
5. Precios: solo si el objetivo es 'vender' y el contexto los tiene.
"""

USER_PROMPT_TEMPLATE = """CONTEXTO RECUPERADO (usa SOLO esto):
{context}

TAREA:
- Tema: {tema}
- Formato: {formato} (reel | story | post | blog)
- Objetivo: {objetivo} (vender | educar | entretener | fidelizar | anunciar)

Genera SOLO el JSON con esta estructura exacta:
{{
  "copy": "texto completo del post/reel/story/blog",
  "shots_list": ["plano 1", "plano 2", ...] (solo para reel; lista vacía si no),
  "hashtags": ["#clandestino1920", "#salamanca", ...],
  "alt_text": "descripción accesible de la imagen/video",
  "citations": ["doc_id_1", "doc_id_2", ...]
}}"""

# ─── FUNCIONES ───────────────────────────────────────────────────────────

def generate_creative(tema: str, formato: str, objetivo: str, feedback: str = "") -> CreativeOutput:
    """Pipeline completo: busca → prompt → LLM → parse → valida."""
    
    # 1. Busca contexto relevante (mezcla: item + lore + tecnica + evento)
    query = f"{tema} {formato} {objetivo}"
    ctx_results = search_context(query, top_k=8)
    
    # 2. Construye prompt CON FEEDBACK SI EXISTE
    context_str = build_context_str(ctx_results)
    
    feedback_block = f"\n\nFEEDBACK DE QUALITY AGENT (mejora esto):\n{feedback}\n" if feedback else ""
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context_str + feedback_block,
        tema=tema,
        formato=formato,
        objetivo=objetivo
    )
    
    # 3. Llama LLM con structured output (JSON mode)
    completion = groq.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    
    raw = completion.choices[0].message.content
    data = json.loads(raw)
    
    # 4. Valida y completa
    citations = [r["id"] for r in ctx_results]
    
    return CreativeOutput(
        copy=data.get("copy", "").strip(),
        shots_list=data.get("shots_list", []) if formato == "reel" else [],
        hashtags=list(dict.fromkeys(data.get("hashtags", []) + ["#clandestino1920", "#salamanca", "#speakeasy"])),
        alt_text=data.get("alt_text", "").strip(),
        citations=citations,
    )



def search_context(query: str, top_k: int = 5, filter_tipo: Optional[str] = None,
                   intentos: int = 4) -> list[dict]:
    """
    Busca en Qdrant y devuelve lista de dicts con text, payload, score.

    Si la red falla (DNS caído, timeout), reintenta con espera creciente.
    Si tras los intentos sigue sin haber conexión, devuelve [] y avisa:
    el pipeline continúa con la ficha de la carta en vez de abortar.
    """
    vec = embed_model.encode(query).tolist()

    qfilter = None
    if filter_tipo:
        qfilter = Filter(must=[FieldCondition(key="tipo", match=MatchAny(any=[filter_tipo]))])

    ultimo = None
    for i in range(intentos):
        try:
            res = qdrant.query_points(
                collection_name=COLLECTION,
                query=vec,
                limit=top_k,
                with_payload=True,
                query_filter=qfilter
            ).points
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "text": r.payload["text"],
                    "source": r.payload.get("source"),
                    "tipo": r.payload.get("tipo"),
                    "nombre": r.payload.get("nombre"),
                }
                for r in res
            ]
        except Exception as e:  # noqa: BLE001  (red, DNS, timeout, 5xx)
            ultimo = e
            if i < intentos - 1:
                espera = 2 * (i + 1)
                print(f"  ⚠ Qdrant no responde ({type(e).__name__}), reintento en {espera}s...")
                time.sleep(espera)

    print(f"  ⚠ Sin conexión con Qdrant tras {intentos} intentos: {ultimo}")
    print("    Sigo sin contexto recuperado (solo con la ficha de la carta).")
    return []

def build_context_str(results: list[dict]) -> str:
    """Convierte resultados en bloque de contexto para el prompt."""
    blocks = []
    for r in results:
        header = f"[{r['id']}] ({r['source']}/{r['tipo']}"
        if r.get('nombre'):
            header += f" — {r['nombre']}"
        header += f") score={r['score']:.3f}"
        blocks.append(f"{header}\n{r['text']}")
    return "\n\n---\n\n".join(blocks)

# ─── MAIN / CLI ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 4:
        print("Uso: python creative_agent.py <tema> <formato> <objetivo>")
        print("Ejemplo: python creative_agent.py \"Old Fashioned\" reel vender")
        print("Formatos: reel, story, post, blog")
        print("Objetivos: vender, educar, entretener, fidelizar, anunciar")
        sys.exit(1)
    
    tema = sys.argv[1]
    formato = sys.argv[2].lower()
    objetivo = sys.argv[3].lower()
    
    if formato not in ("reel", "story", "post", "blog"):
        print(f"Formato '{formato}' no válido. Usa: reel, story, post, blog")
        sys.exit(1)
    
    print(f"🎬 Generando {formato.upper()} sobre '{tema}' (objetivo: {objetivo})...")
    
    output = generate_creative(tema, formato, objetivo)
    
    print("\n" + "="*60)
    print(output.to_json())
    print("="*60)
    
    # Guarda también en archivo para revisar
    out_file = Path(f"output_{formato}_{tema.replace(' ', '_').lower()}.json")
    out_file.write_text(output.to_json(), encoding="utf-8")
    print(f"\n💾 Guardado en: {out_file}")

if __name__ == "__main__":
    main()