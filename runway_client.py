# runway_client.py — Runway (API oficial: api.dev.runwayml.com)
#
# Lo que fallaba en la versión anterior:
#   1. La URL era api.runwayml.com  →  la correcta es api.dev.runwayml.com
#   2. Se llamaba a /v1/generations; ahora son /v1/text_to_video y /v1/image_to_video
#      y el estado se consulta en /v1/tasks/{id}
#   3. Gen-3/Gen-4 necesitan una imagen de partida; para texto→vídeo se usa veo3.1
#
# Estado: la clave del .env es válida, pero la cuenta NO tiene créditos
# ("You do not have enough credits to run this task"). Listo para el día que recargues.
# El resto del proyecto no depende de este archivo.

import os
import time
from pathlib import Path

import requests

ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("RUNWAY_API_KEY")
BASE = "https://api.dev.runwayml.com/v1"
VERSION = "2024-11-06"


def _headers() -> dict:
    if not API_KEY:
        raise RuntimeError("Falta RUNWAY_API_KEY en .env")
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Runway-Version": VERSION,
    }


def generate_video(prompt: str, aspect: str = "720:1280", duration: int = 8,
                   model: str = "veo3.1_fast") -> str:
    """Texto → vídeo. Para reels: aspect='720:1280' (vertical). Devuelve task id."""
    payload = {"model": model, "promptText": prompt, "ratio": aspect, "duration": duration}
    r = requests.post(f"{BASE}/text_to_video", headers=_headers(), json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Runway ERROR {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def animate_image(image_url: str, prompt: str, duration: int = 5,
                  model: str = "gen4_turbo") -> str:
    """Imagen → vídeo (más barato). image_url debe ser pública o data URL."""
    payload = {"model": model, "promptImage": image_url, "promptText": prompt, "duration": duration}
    r = requests.post(f"{BASE}/image_to_video", headers=_headers(), json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Runway ERROR {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def wait_for_video(task_id: str, poll_interval: int = 10, timeout_s: int = 900) -> str:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = requests.get(f"{BASE}/tasks/{task_id}", headers=_headers(), timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"Runway ERROR {r.status_code}: {r.text[:400]}")
        data = r.json()
        estado = data.get("status")
        if estado == "SUCCEEDED":
            return data["output"][0]
        if estado in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway falló: {data.get('failure')}")
        print(f"  ⏳ Generando... ({estado})")
        time.sleep(poll_interval)
    raise TimeoutError("Runway tardó demasiado")


def download_video(url: str, output_path: Path) -> Path:
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path
