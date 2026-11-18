#!/usr/bin/env python3
"""
image_client.py — Genera las imágenes de cada plano con Gemini (nano banana).

Es la alternativa gratis a Runway/Kling: en vez de vídeo generado, generamos
una foto vertical por plano y luego reel_builder.py le da movimiento (Ken Burns).

Uso suelto:
    python image_client.py "copa de whisky bajo luz ámbar" salida.png
"""

import base64
import os
import time
import sys
from pathlib import Path

import requests

ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Falta GEMINI_API_KEY en .env")

MODEL = os.environ.get("IMAGE_MODEL", "gemini-2.5-flash-image")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# Estilo común: así todos los planos parecen del mismo spot
STYLE = (
    "Cinematic photograph, 1920s speakeasy in Salamanca, dim warm amber lamp light, "
    "dark walnut and brass, film grain, shallow depth of field, photorealistic, "
    "vertical 9:16 composition, no text, no watermark"
)


def _post_with_retry(url: str, body: dict, attempts: int = 4) -> requests.Response:
    """POST con reintentos: en Windows el DNS falla a ratos y no queremos perder el plano."""
    last = None
    for i in range(attempts):
        try:
            r = requests.post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
                json=body,
                timeout=180,
            )
            if r.status_code in (429, 500, 502, 503, 504) and i < attempts - 1:
                last = RuntimeError(f"Gemini ERROR {r.status_code}: {r.text[:200]}")
                time.sleep(3 * (i + 1))
                continue
            return r
        except requests.exceptions.ConnectionError as e:
            last = e
            print(f"  ⚠ conexión/DNS falló (intento {i+1}/{attempts}), reintento...")
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"No se pudo conectar con Gemini tras {attempts} intentos: {last}")


def generate_image(prompt: str, output_path: Path, style: str = STYLE) -> Path:
    """Genera una imagen 9:16 y la guarda en output_path."""
    full_prompt = f"{prompt}. {style}" if style else prompt

    body = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"imageConfig": {"aspectRatio": "9:16"}},
    }

    r = _post_with_retry(URL, body)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini ERROR {r.status_code}: {r.text[:400]}")

    data = r.json()
    parts = data["candidates"][0]["content"].get("parts", [])
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if inline:
            raw = base64.b64decode(inline["data"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(raw)
            return output_path

    raise RuntimeError(f"Gemini no devolvió imagen: {str(data)[:300]}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Uso: python image_client.py "<descripción del plano>" salida.png')
        sys.exit(1)
    out = generate_image(sys.argv[1], Path(sys.argv[2]))
    print(f"💾 {out}")
