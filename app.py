#!/usr/bin/env python3
"""
app.py — Panel para generar carruseles de Instagram de Clandestino 1920.

Arranca un servidor local, abre el navegador y te deja:
  · ver la carta y las fotos del local
  · elegir un cóctel
  · generar su carrusel (imágenes + textos + ZIP) con un botón

Uso:
    python app.py
    python app.py --port 8000
    python app.py --no-browser
"""

import argparse
import json
import threading
import traceback
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from PIL import Image

from carousel_agent import ASSETS, CARTA_PATH, OUT_ROOT, _cover, make_carousel, mensaje_red

ROOT = Path(__file__).parent
app = Flask(__name__, template_folder="templates")

JOBS: dict[str, dict] = {}
LOCK = threading.Lock()

CATEGORIAS = ["Cócteles", "Destilados", "Cervezas", "Vinos", "Otros"]


def load_carta() -> list[dict]:
    return json.loads(CARTA_PATH.read_text(encoding="utf-8"))


def interior_photos() -> list[Path]:
    folder = ASSETS / "interior"
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))


def carruseles_disponibles() -> list[dict]:
    """Carruseles ya generados en carruseles/, del más nuevo al más viejo."""
    items = []
    if not OUT_ROOT.exists():
        return items

    carpetas = sorted((p for p in OUT_ROOT.iterdir() if p.is_dir()),
                      key=lambda p: p.stat().st_mtime, reverse=True)

    for d in carpetas:
        slides = sorted(d.glob("slide_*.jpg"))
        if not slides:
            continue
        info = {}
        if (d / "info.json").exists():
            try:
                info = json.loads((d / "info.json").read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                info = {}
        caption = d / "caption.txt"
        items.append({
            "slug": d.name,
            "tema": info.get("tema") or d.name.rsplit("_", 1)[0].replace("_", " "),
            "fecha": d.name.rsplit("_", 1)[-1],
            "slides": [f"/media/carrusel/{d.name}/{s.name}" for s in slides],
            "caption": caption.read_text(encoding="utf-8").strip() if caption.exists() else "",
        })
    return items


@app.route("/")
def index():
    items = load_carta()
    fotos = [p.name for p in interior_photos()]
    return render_template(
        "panel.html",
        items=items,
        categorias=CATEGORIAS,
        fotos=fotos,
        total=len(items),
    )


@app.route("/api/carruseles")
def api_carruseles():
    return jsonify(carruseles_disponibles())


@app.route("/media/interior/<path:name>")
def media_interior(name):
    return send_from_directory(ASSETS / "interior", name)


@app.route("/media/carrusel/<path:rest>")
def media_carrusel(rest):
    return send_from_directory(OUT_ROOT, rest)


@app.route("/api/carta")
def api_carta():
    return jsonify(load_carta())


def _run_job(job_id: str, nombre: str, objetivo: str, slides: int):
    def log(msg: str, stage: str | None = None, **extra):
        with LOCK:
            JOBS[job_id]["log"].append(msg)
            JOBS[job_id]["events"].append({"stage": stage, "msg": msg, **extra})

    try:
        res = make_carousel(nombre, objetivo, slides, progress=log)
        # URLs públicas de los archivos (sin url_for: aquí no hay contexto de petición)
        rel_dir = Path(res["dir"]).relative_to(OUT_ROOT).as_posix()
        rel_zip = Path(res["zip"]).relative_to(OUT_ROOT).as_posix()
        with LOCK:
            JOBS[job_id].update({
                "status": "ok",
                "result": {
                    "tema": res["tema"],
                    "slides": [f"/media/carrusel/{rel_dir}/{Path(s).name}"
                               for s in res["slides"]],
                    "zip": f"/media/carrusel/{rel_zip}",
                    "caption": res["caption"],
                    "dir": res["dir"],
                    "evaluacion": res.get("evaluacion"),
                },
            })
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        bajo = msg.lower()
        es_red = any(k in bajo for k in ("getaddrinfo", "connection", "timeout", "429", "quota"))
        with LOCK:
            JOBS[job_id].update({
                "status": "error",
                "error": mensaje_red(e, "el sistema") if es_red else msg,
                "trace": "" if es_red else traceback.format_exc()[-1200:],
            })


@app.route("/api/generar", methods=["POST"])
def api_generar():
    body = request.get_json(force=True) or {}
    nombre = (body.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "Falta el nombre del cóctel"}), 400

    objetivo = body.get("objetivo") or "vender"
    slides = int(body.get("slides") or 5)
    slides = max(3, min(10, slides))

    job_id = uuid.uuid4().hex[:8]
    with LOCK:
        JOBS[job_id] = {"status": "running", "log": [], "events": [],
                        "result": None, "error": None}

    threading.Thread(
        target=_run_job, args=(job_id, nombre, objetivo, slides), daemon=True
    ).start()

    return jsonify({"job": job_id})


@app.route("/api/job/<job_id>")
def api_job(job_id):
    with LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "job desconocido"}), 404
        return jsonify({
            "status": job["status"],
            "log": job["log"],
            "events": job.get("events", []),
            "result": job["result"],
            "error": job["error"],
            "trace": job.get("trace"),
        })


def ensure_interior():
    """Si no hay fotos del local, las genera una vez con Gemini."""
    folder = ASSETS / "interior"
    if interior_photos():
        return
    from image_client import generate_image

    folder.mkdir(parents=True, exist_ok=True)
    prompts = [
        "Empty speakeasy bar interior seen from the counter, dark walnut bar, brass rails, "
        "amber pendant lamps, shelves of bottles, velvet stools",
        "Corner booth inside a 1920s speakeasy: velvet armchairs, small round marble table, "
        "candle, framed vintage photographs on dark green wall",
        "The hidden entrance: a heavy wooden door half open with warm light spilling out, "
        "brick wall, small brass plaque, dim corridor",
        "Bartender in waistcoat pouring a cocktail behind a brass-and-walnut bar, "
        "shaker in hand, warm backlit bottles",
    ]
    print("🖼  Generando fotos del local (solo la primera vez)...")
    for i, p in enumerate(prompts, start=1):
        raw = folder / f".raw_{i}.png"
        generate_image(p, raw)
        img = Image.open(raw).convert("RGB")
        img = _cover(img, 1080, 1350)
        img.save(folder / f"interior_{i:02d}.jpg", "JPEG", quality=88, optimize=True)
        raw.unlink()
        print(f"   interior_{i:02d}.jpg")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    ensure_interior()

    url = f"http://127.0.0.1:{a.port}/"
    if not a.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\n🍸 Panel Clandestino 1920 → {url}   (Ctrl+C para parar)\n")
    app.run(host="127.0.0.1", port=a.port, debug=False, threaded=True)
