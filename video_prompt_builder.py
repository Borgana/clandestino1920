# video_prompt_builder.py
import json
from pathlib import Path

def build_video_prompts(creative_json: dict, style: str = "cinematic speakeasy 1920s, dim warm amber lighting, film grain, 8k photorealistic") -> list[dict]:
    """
    Convierte tu JSON + shots_list → prompts optimizados para Runway/Veo/Luma.
    """
    shots = creative_json.get("shots_list", [])
    tema = creative_json.get("tema", "cocktail")
    
    prompts = []
    for i, shot in enumerate(shots):
        prompts.append({
            "shot_index": i,
            "prompt": f"{shot}, {style}",
            "duration_seconds": 3,
            "aspect_ratio": "9:16",
            "camera_motion": "slow push in" if i % 2 == 0 else "slow parallax",
        })
    
    # Plano final CTA
    prompts.append({
        "shot_index": len(shots),
        "prompt": f"Elegant text animation: 'Reserva tu experiencia en enlace bio 🔗', {style}, minimal typography",
        "duration_seconds": 2,
        "aspect_ratio": "9:16",
    })
    
    return prompts


if __name__ == "__main__":
    # Test rápido con tu FINAL_reel_old_fashioned.json
    test_file = Path("FINAL_reel_old_fashioned.json")
    if test_file.exists():
        creative = json.loads(test_file.read_text())
        creative["tema"] = "Old Fashioned"
        prompts = build_video_prompts(creative)
        print(json.dumps(prompts, indent=2, ensure_ascii=False))
