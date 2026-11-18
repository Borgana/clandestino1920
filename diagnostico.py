#!/usr/bin/env python3
"""
diagnostico.py — Comprueba en 10 segundos si todo lo que necesita el carrusel responde.

Es lo que hay que ejecutar si algo falla antes de presentar:
  python diagnostico.py

Revisa DNS, base de datos (Qdrant), modelo de texto (Groq) e IA de imágenes (Gemini).
"""

import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    import os
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def cabecera(t):
    print(f"\n{t}")
    print("─" * len(t))


def dns(host: str) -> bool:
    for intento in range(3):
        try:
            t = time.time()
            socket.gethostbyname(host)
            print(f"  ✅ {host} resuelve ({(time.time()-t)*1000:.0f} ms)")
            return True
        except Exception:  # noqa: BLE001
            if intento < 2:
                time.sleep(1.5)
    print(f"  ❌ {host}: el DNS no resuelve. Cambia de red o de DNS (1.1.1.1) y reintenta.")
    return False


def main():
    print("Diagnóstico de Clandestino 1920")

    cabecera("1. Internet y DNS")
    import os
    qurl = os.environ.get("QDRANT_URL", "")
    host_qdrant = urlparse(qurl).hostname or ""
    ok_dns = True
    for h in [x for x in (host_qdrant, "api.groq.com", "generativelanguage.googleapis.com") if x]:
        ok_dns = dns(h) and ok_dns

    cabecera("2. Base de datos (Qdrant)")
    try:
        from qdrant_client import QdrantClient
        c = QdrantClient(url=qurl, api_key=os.environ.get("QDRANT_API_KEY"), timeout=15)
        n = c.count(collection_name="clandestino_kb", exact=True).count
        print(f"  ✅ conectado · {n} fragmentos indexados")
        if n == 0:
            print("  ⚠ la colección está vacía: ejecuta  python ingest.py")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ no responde: {e}")

    cabecera("3. Modelo de texto (Groq)")
    try:
        from groq import Groq
        g = Groq(api_key=os.environ.get("GROQ_API_KEY"), timeout=20)
        r = g.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": "responde solo: ok"}],
            max_tokens=5,
        )
        print(f"  ✅ responde: {r.choices[0].message.content.strip()[:30]}")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ no responde: {e}")

    cabecera("4. IA de imágenes (Gemini)")
    try:
        import requests
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": key}, timeout=20)
        if r.status_code == 200:
            print(f"  ✅ clave válida · {len(r.json().get('models', []))} modelos disponibles")
        elif r.status_code == 429:
            print("  ⚠ clave válida pero sin cuota ahora mismo (429)")
        else:
            print(f"  ❌ HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ no responde: {e}")

    cabecera("Resumen")
    print("  Si los cuatro pasos salen en verde, el panel funcionará.")
    print("  Si falla solo el DNS, es la red: reintenta o cambia de wifi.")
    return 0 if ok_dns else 1


if __name__ == "__main__":
    sys.exit(main())
