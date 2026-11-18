#!/usr/bin/env python3
"""
Pipeline completo: Creative → Quality → (regenera si < 7) → Output final
Uso: python pipeline.py "Old Fashioned" reel vender
"""

import sys
import json
from pathlib import Path

# Importa tus agentes
from creative_agent import generate_creative, search_context, build_context_str
from quality_agent import evaluate_creative, QualityResult

MAX_ATTEMPTS = 3
THRESHOLD = 7.0

def run_pipeline(tema: str, formato: str, objetivo: str) -> dict:
    feedback = ""
    context_results = search_context(f"{tema} {formato} {objetivo}", top_k=8)
    context_str = build_context_str(context_results)
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n🔄 INTENTO {attempt}/{MAX_ATTEMPTS}")
        
        # 1. CREATIVE
        creative = generate_creative(tema, formato, objetivo, feedback=feedback)
        creative_dict = {
            "copy": creative.copy,
            "shots_list": creative.shots_list,
            "hashtags": creative.hashtags,
            "alt_text": creative.alt_text,
            "citations": creative.citations,
        }
        
        # 2. QUALITY
        result: QualityResult = evaluate_creative(
            tema=tema,
            formato=formato,
            objetivo=objetivo,
            creative_output=creative_dict,
            context_str=context_str,
            feedback_previo=feedback
        )
        
        print(f"   Score: {result.scores.overall}/10  {'✅' if result.approved else '❌'}")
        print(f"   Feedback: {result.feedback[:120]}...")
        
        if result.approved:
            print(f"\n✅ APROBADO EN INTENTO {attempt}")
            # Añade metadata de quality al output final
            creative_dict["_quality"] = {
                "scores": result.scores.to_dict(),
                "attempts": attempt,
                "final_feedback": result.feedback
            }
            return creative_dict
        
        # 3. PREPARA SIGUIENTE INTENTO
        feedback = result.feedback
    
    print(f"\n⚠️  MÁXIMOS INTENTOS ALCANZADOS — Devuelve lo mejor")
    creative_dict["_quality"] = {
        "scores": result.scores.to_dict(),
        "attempts": MAX_ATTEMPTS,
        "final_feedback": "Max attempts reached"
    }
    return creative_dict


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python pipeline.py <tema> <formato> <objetivo>")
        print("Ej: python pipeline.py \"Old Fashioned\" reel vender")
        sys.exit(1)
    
    tema, formato, objetivo = sys.argv[1], sys.argv[2], sys.argv[3]
    
    final_output = run_pipeline(tema, formato, objetivo)
    
    # Guarda resultado final
    out_file = Path(f"FINAL_{formato}_{tema.replace(' ', '_').lower()}.json")
    out_file.write_text(json.dumps(final_output, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n💾 Guardado en: {out_file}")
    print(f"📊 Score final: {final_output['_quality']['scores']['overall']}/10")