#!/usr/bin/env python3
"""
sync_web.py — Pasa los carruseles generados a la web (para GitHub y Vercel).

Copia a web/img/carruseles/ los carruseles nuevos, refresca web/data/carruseles.json
y copia las fotos del local. Después solo hay que hacer commit y push.

Uso:  python sync_web.py
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
WEB = ROOT / "web"
CARRUSELES = ROOT / "carruseles"


def slug_sin_acentos(texto: str) -> str:
    import unicodedata
    limpio = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return limpio.lower().replace(" ", "_").replace("/", "-")


def main():
    destino = WEB / "img" / "carruseles"
    destino.mkdir(parents=True, exist_ok=True)

    # 1. fotos del local
    (WEB / "img" / "local").mkdir(parents=True, exist_ok=True)
    for foto in (ROOT / "assets" / "interior").glob("interior_*.jpg"):
        shutil.copy2(foto, WEB / "img" / "local" / foto.name)

    # 2. carta
    (WEB / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "data" / "carta.json", WEB / "data" / "carta.json")

    # 3. carruseles
    items = []
    for carpeta in sorted(p for p in CARRUSELES.iterdir() if p.is_dir()):
        slides = sorted(carpeta.glob("slide_*.jpg"))
        if not slides:
            continue

        nombre = slug_sin_acentos(carpeta.name)  # sin tildes: rompen las URLs
        out = destino / nombre
        out.mkdir(parents=True, exist_ok=True)
        for s in slides:
            shutil.copy2(s, out / s.name)
        caption = carpeta / "caption.txt"
        if caption.exists():
            shutil.copy2(caption, out / "caption.txt")

        info = {}
        if (carpeta / "info.json").exists():
            info = json.loads((carpeta / "info.json").read_text(encoding="utf-8"))

        items.append({
            "slug": nombre,
            "tema": info.get("tema") or carpeta.name.rsplit("_", 1)[0].replace("_", " "),
            "fecha": carpeta.name.rsplit("_", 1)[-1],
            "slides": [f"img/carruseles/{nombre}/{s.name}" for s in slides],
            "caption": caption.read_text(encoding="utf-8").strip() if caption.exists() else "",
        })

    (WEB / "data" / "carruseles.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ {len(items)} carruseles sincronizados en web/")
    for it in items:
        print(f"   · {it['tema']:22} {len(it['slides'])} slides")
    print("\nAhora:  git add -A && git commit -m 'nuevos carruseles' && git push")
    print("Y para publicar:  vc deploy web --prod")


if __name__ == "__main__":
    main()
