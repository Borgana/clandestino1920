# luma_client.py
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
LUMA_API_KEY = os.environ.get("LUMA_API_KEY")
BASE = "https://api.lumalabs.ai/dream-machine/v1"

if not LUMA_API_KEY:
    raise RuntimeError("Falta LUMA_API_KEY en .env")

HEADERS = {
    "Authorization": f"Bearer {LUMA_API_KEY}",
    "Content-Type": "application/json"
}

def generate_video(prompt: str, aspect_ratio: str = "9:16", duration: int = 5) -> str:
    """Lanza generación en Luma. Devuelve generation_id."""
    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": str(duration),  # "5" o "10"
        "loop": False
    }
    r = requests.post(f"{BASE}/generations", headers=HEADERS, json=payload)
    
    if r.status_code != 200:
        print(f"❌ Luma ERROR {r.status_code}: {r.text}")
        r.raise_for_status()
    
    return r.json()["id"]

def wait_for_video(gen_id: str, poll_interval: int = 10) -> str:
    """Espera y devuelve URL del video."""
    while True:
        r = requests.get(f"{BASE}/generations/{gen_id}", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        state = data["state"]
        if state == "completed":
            return data["assets"]["video"]
        if state == "failed":
            raise RuntimeError(f"Luma failed: {data.get('failure_reason')}")
        print(f"  ⏳ Generando... ({state})")
        time.sleep(poll_interval)

def download_video(url: str, output_path: Path) -> Path:
    r = requests.get(url, stream=True)
    r.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path