# test_video.py (VERSIÓN LUMA - COPIA ESTO COMPLETO)
import json
from pathlib import Path
from video_prompt_builder import build_video_prompts
from luma_client import generate_video, wait_for_video, download_video  # ← CAMBIO AQUÍ

# 1. Carga tu JSON final
creative = json.load(open('FINAL_reel_old_fashioned.json', encoding='utf-8'))
creative['tema'] = 'Old Fashioned'

# 2. Construye prompts de video
prompts = build_video_prompts(creative)
first = prompts[0]
print(f'🎬 Generando plano 0: {first["prompt"][:100]}...')

# 3. Lanza en Luma (duration 5s por defecto)
task_id = generate_video(first['prompt'], first['aspect_ratio'], 5)
print(f'   Generation ID: {task_id}')

# 4. Espera a que termine (Luma tarda más, ~2-3 min)
url = wait_for_video(task_id)
print(f'   ✅ Listo: {url}')

# 5. Descarga MP4
out = Path('videos') / 'shot_00_old_fashioned.mp4'
download_video(url, out)
print(f'   💾 Guardado en: {out}')
