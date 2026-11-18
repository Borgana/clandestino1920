#!/usr/bin/env python3
"""
Quality Agent Clandestino 1920
Evalúa salida del Creative Agent y devuelve scores + feedback.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from groq import Groq

# ─── CONFIG ──────────────────────────────────────────────────────────────
LLM_MODEL = "openai/gpt-oss-20b"  # mismo que creative_agent

# ─── CARGA .ENV ──────────────────────────────────────────────────────────
ENV_PATH = Path(".env")
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Falta GROQ_API_KEY en .env")

groq = Groq(api_key=GROQ_API_KEY)

# ─── ESTRUCTURAS ─────────────────────────────────────────────────────────

@dataclass
class QualityScores:
    brand_voice: int        # 0-10
    safety: int             # 0-10
    engagement: int         # 0-10
    objective_fit: int      # 0-10
    rag_usage: int          # 0-10
    
    @property
    def overall(self) -> float:
        # Pesos: seguridad 2x, resto 1x
        return (self.brand_voice + 2*self.safety + self.engagement + 
                self.objective_fit + self.rag_usage) / 6

    def passed(self, threshold: float = 7.0) -> bool:
        return self.overall >= threshold

    def to_dict(self):
        return {
            "brand_voice": self.brand_voice,
            "safety": self.safety,
            "engagement": self.engagement,
            "objective_fit": self.objective_fit,
            "rag_usage": self.rag_usage,
            "overall": round(self.overall, 2),
            "passed": self.passed()
        }

@dataclass
class QualityResult:
    scores: QualityScores
    feedback: str           # Texto para regenerar
    approved: bool

# ─── PROMPT DE EVALUACIÓN ────────────────────────────────────────────────

EVAL_SYSTEM_PROMPT = """Eres el **Quality Controller** de Clandestino 1920.
Tu trabajo: evaluar contenido generado para Instagram/Facebook/Web del speakeasy.
Eres estricto pero justo. Puntúas 0-10 en 5 dimensiones y das feedback accionable.

DIMENSIONES:
1. BRAND VOICE (0-10): ¿Suena a Clandestino? Misterioso, elegante, "vosotros", "guardianes", "ritual", "ceremonia", "secreto", "conquista". Emojis estratégicos 🕵🏼🥃☕✨🖤🔑. NO: genérico, comercial, "venid a disfrutar".
2. SAFETY (0-10): ¿Alérgenos correctos? ¿Precios reales de carta? ¿No inventa cócteles? ¿No promete lo que no hay? FALLO GRAVE = 0-3.
3. ENGAGEMENT (0-10): ¿Hook en 3s? ¿CTA claro y suave? ¿Formato nativo? (Reel: shots visuales; Story: interactivo; Post: carousel/foto; Blog: SEO).
4. OBJECTIVE_FIT (0-10): ¿Cumple el objetivo? vender→precio+reserva; educar→explica técnica; entretener→historia+lore; fidelizar→exclusividad; anunciar→evento+fecha.
5. RAG_USAGE (0-10): ¿Usa SOLO info del contexto? ¿Citations reales? ¿No alucina? ¿Respeta carta/lore/técnicas/alergenos/eventos?

OUTPUT OBLIGATORIO (JSON estricto):
{
  "scores": {"brand_voice": 8, "safety": 9, "engagement": 7, "objective_fit": 8, "rag_usage": 9},
  "feedback": "Texto concreto para mejorar: qué falla, qué añadir, qué quitar. Si todo bien: 'APROBADO'.",
  "approved": true
}"""

EVAL_USER_TEMPLATE = """CONTEXTO RECUPERADO (fuente de verdad):
{context}

CONTENIDO A EVALUAR:
- Tema: {tema}
- Formato: {formato}
- Objetivo: {objetivo}
- Copy generado: {copy}
- Shots list: {shots_list}
- Hashtags: {hashtags}
- Alt text: {alt_text}
- Citations usadas: {citations}

FEEDBACK PREVIO (si hay regeneración):
{feedback_previo}

EVALÚA Y DEVUELVE SOLO EL JSON."""


# ─── FUNCIONES ───────────────────────────────────────────────────────────

def evaluate_creative(
    tema: str,
    formato: str,
    objetivo: str,
    creative_output: dict,      # dict con copy, shots_list, hashtags, alt_text, citations
    context_str: str,           # contexto usado (para verificar RAG)
    feedback_previo: str = ""
) -> QualityResult:
    """Llama al LLM juez y parsea resultado."""
    
    user_prompt = EVAL_USER_TEMPLATE.format(
        context=context_str[:3000],  # recorta si muy largo
        tema=tema,
        formato=formato,
        objetivo=objetivo,
        copy=creative_output.get("copy", ""),
        shots_list=creative_output.get("shots_list", []),
        hashtags=creative_output.get("hashtags", []),
        alt_text=creative_output.get("alt_text", ""),
        citations=creative_output.get("citations", []),
        feedback_previo=feedback_previo or "Ninguno (primera generación)"
    )
    
    completion = groq.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,  # más determinista para evaluación
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    
    raw = completion.choices[0].message.content
    data = json.loads(raw)
    
    scores = QualityScores(
        brand_voice=data["scores"]["brand_voice"],
        safety=data["scores"]["safety"],
        engagement=data["scores"]["engagement"],
        objective_fit=data["scores"]["objective_fit"],
        rag_usage=data["scores"]["rag_usage"],
    )
    
    return QualityResult(
        scores=scores,
        feedback=data["feedback"],
        approved=data["approved"]
    )


# ─── CLI TEST ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test rápido: evalúa el output_reel_old_fashioned.json generado antes
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        test_file = "output_reel_old_fashioned.json"
    
    if not Path(test_file).exists():
        print(f"❌ No existe {test_file}")
        sys.exit(1)
    
    creative = json.loads(Path(test_file).read_text())
    
    # Contexto dummy para test (en pipeline real vendrá de search_context)
    context = "Old Fashioned: whisky, azúcar, angostura, twist naranja. Precio 7.5€. Lore: speakeasy 1920, guardianes de la noche."
    
    result = evaluate_creative(
        tema="Old Fashioned",
        formato="reel",
        objetivo="vender",
        creative_output=creative,
        context_str=context
    )
    
    print("\n" + "="*60)
    print("📊 QUALITY REPORT")
    print("="*60)
    print(f"Overall: {result.scores.overall}/10  {'✅ APROBADO' if result.approved else '❌ RECHAZADO'}")
    print(f"Brand Voice: {result.scores.brand_voice}/10")
    print(f"Safety:      {result.scores.safety}/10  (peso x2)")
    print(f"Engagement:  {result.scores.engagement}/10")
    print(f"Obj. Fit:    {result.scores.objective_fit}/10")
    print(f"RAG Usage:   {result.scores.rag_usage}/10")
    print(f"\nFeedback: {result.feedback}")
    print("="*60)