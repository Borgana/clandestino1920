# kling_client.py — Kling AI (API oficial: api.klingai.com)
#
# OJO: la API oficial NO usa una clave simple. Usa un par Access Key / Secret Key
# que se firma en un token JWT en cada petición. Las claves se sacan en:
#     https://app.klingai.com/global/dev  →  API Keys
# y en el .env van así:
#     KLING_ACCESS_KEY=...
#     KLING_SECRET_KEY=...
#
# Estado: escrito según la documentación oficial, SIN probar todavía
# (hace falta una cuenta con créditos). El resto del proyecto no depende de esto.

import base64
import hashlib
import hmac
import json
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

ACCESS_KEY = os.environ.get("KLING_ACCESS_KEY")
SECRET_KEY = os.environ.get("KLING_SECRET_KEY")
BASE = "https://api.klingai.com/v1"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(access_key: str, secret_key: str, ttl: int = 1800) -> str:
    """Token JWT HS256 que exige Kling (válido 30 min por defecto)."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": access_key,
        "exp": int(time.time()) + ttl,
        "nbf": int(time.time()) - 5,
    }
    sin_firmar = (
        _b64(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64(json.dumps(payload, separators=(",", ":")).encode())
    )
    firma = hmac.new(secret_key.encode(), sin_firmar.encode(), hashlib.sha256).digest()
    return f"{sin_firmar}.{_b64(firma)}"


def _headers() -> dict:
    if not ACCESS_KEY or not SECRET_KEY:
        raise RuntimeError(
            "Faltan KLING_ACCESS_KEY y KLING_SECRET_KEY en .env "
            "(se sacan en https://app.klingai.com/global/dev)"
        )
    return {
        "Authorization": f"Bearer {make_jwt(ACCESS_KEY, SECRET_KEY)}",
        "Content-Type": "application/json",
    }


def generate_video(prompt: str, aspect: str = "9:16", duration: int = 5,
                   model: str | None = None, mode: str = "std",
                   negative_prompt: str = "text, watermark, logo, distorted hands") -> str:
    """Lanza la generación. Devuelve task_id."""
    payload = {
        "model_name": model or os.environ.get("KLING_MODEL", "kling-v2-1"),
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "cfg_scale": 0.5,
        "mode": mode,               # std (más barato) | pro
        "duration": str(duration),  # "5" o "10"
        "aspect_ratio": aspect,
    }
    r = requests.post(f"{BASE}/videos/text2video", headers=_headers(), json=payload, timeout=60)
    data = r.json() if r.content else {}
    if r.status_code != 200 or data.get("code") not in (0, None):
        raise RuntimeError(f"Kling ERROR {r.status_code}: {str(data)[:400]}")
    return data["data"]["task_id"]


def wait_for_video(task_id: str, poll_interval: int = 10, timeout_s: int = 900) -> str:
    """Espera al vídeo y devuelve la URL del MP4."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = requests.get(f"{BASE}/videos/text2video/{task_id}", headers=_headers(), timeout=60)
        data = r.json()
        if r.status_code != 200 or data.get("code") not in (0, None):
            raise RuntimeError(f"Kling ERROR {r.status_code}: {str(data)[:400]}")
        d = data["data"]
        estado = d.get("task_status")
        if estado == "succeed":
            return d["task_result"]["videos"][0]["url"]
        if estado == "failed":
            raise RuntimeError(f"Kling falló: {d.get('task_status_msg')}")
        print(f"  ⏳ Generando... ({estado})")
        time.sleep(poll_interval)
    raise TimeoutError("Kling tardó demasiado")


def download_video(url: str, output_path: Path) -> Path:
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def generate_and_download(prompt: str, output_path: Path, **kwargs) -> Path:
    task_id = generate_video(prompt, **kwargs)
    print(f"   task_id: {task_id}")
    url = wait_for_video(task_id)
    return download_video(url, output_path)
