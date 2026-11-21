# Comandos — copiar y pegar

Todo se lanza desde una terminal en `C:\Proyectos\Clandestino1920`.

---

## 0. Situarse en el proyecto (siempre lo primero)

```powershell
cd C:\Proyectos\Clandestino1920
.\.venv\Scripts\Activate.ps1
```

Si el `Activate` da error de "execution policy", no pasa nada: usa siempre
`.\.venv\Scripts\python.exe` en lugar de `python` y listo.

---

## 1. Arrancar la demo (el panel)

```powershell
cd C:\Proyectos\Clandestino1920
.\.venv\Scripts\python.exe app.py
```

Se abre solo en **http://127.0.0.1:5000**. Para pararlo: `Ctrl+C`.

> Atajo: doble clic en **`iniciar-demo.bat`** (hace lo mismo).

---

## 2. Publicar los cambios (GitHub + Vercel)

```powershell
cd C:\Proyectos\Clandestino1920
.\.venv\Scripts\python.exe sync_web.py
git add -A
git commit -m "cambios"
git push
vc deploy web --prod --project clandestino1920
```

`sync_web.py` copia los carruseles nuevos a `web/` para que salgan en la galería.

> Atajo: doble clic en **`publicar.bat`** (hace los cuatro pasos y se para si algo falla).

---

## 3. Si algo no funciona

```powershell
cd C:\Proyectos\Clandestino1920
.\.venv\Scripts\python.exe diagnostico.py
```

Comprueba DNS, Qdrant, Groq y Gemini. Si falla el DNS: cambia de red (móvil) y reintenta.

---

## 4. Presentar (dos pestañas)

1. **Panel** (demo en vivo): `http://127.0.0.1:5000`
2. **Presentación**: https://clandestino1920.vercel.app
3. **Galería de respaldo**: https://clandestino1920.vercel.app/demo.html

En la presentación: `→` avanza, `←` atrás, `N` notas del orador, `F` pantalla completa.

---

## 5. Otros comandos útiles

```powershell
# Un carrusel sin abrir el panel
.\.venv\Scripts\python.exe carousel_agent.py "Old Fashioned" --slides 5

# Recargar la base de conocimiento (si cambias la carta)
.\.venv\Scripts\python.exe ingest.py

# Regenerar la presentación en PowerPoint (por si acaso)
.\.venv\Scripts\python.exe presentacion\presentacion_build.py
```

---

## URLs y datos a mano

| Qué | Dónde |
|---|---|
| Panel local | http://127.0.0.1:5000 |
| Presentación | https://clandestino1920.vercel.app |
| Galería | https://clandestino1920.vercel.app/demo.html |
| Repositorio | https://github.com/Borgana/clandestino1920 |
| Proyecto Vercel | `clandestino1920` (cuenta `borgana`) |

**Ojo:** el panel solo funciona en tu ordenador. En Vercel está la parte estática
(presentación y galería); generar carruseles necesita Python y las claves del `.env`.
