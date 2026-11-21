@echo off
REM ---------------------------------------------------------------
REM  Clandestino 1920 - publica los cambios en GitHub y Vercel
REM  1) pasa los carruseles nuevos a web/
REM  2) sube el codigo a GitHub
REM  3) despliega la web en Vercel
REM  Doble clic y espera. Si algo falla, la ventana se queda abierta.
REM ---------------------------------------------------------------
cd /d "%~dp0"
REM limpiar variables de Python que puedan venir heredadas de otro programa
set "PYTHONPATH="
set "PYTHONHOME="

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No encuentro .venv. Estas en la carpeta correcta?
    pause
    exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No encuentro "git" en el PATH.
    echo         Abre Git Bash una vez o reinstala Git for Windows.
    pause
    exit /b 1
)

where vc >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No encuentro "vc" (Vercel CLI) en el PATH.
    echo         Instalalo con:  npm i -g vercel
    pause
    exit /b 1
)

echo.
echo === 1/3  Sincronizando carruseles con la web ===
".venv\Scripts\python.exe" sync_web.py
if errorlevel 1 goto fallo

echo.
echo === 2/3  Subiendo a GitHub ===
git add -A
git diff --cached --quiet
if errorlevel 1 goto hay_cambios
echo   (no hay cambios nuevos que commitear)
goto push
:hay_cambios
git commit -m "actualizacion %DATE% %TIME%"
if errorlevel 1 goto fallo

:push
set intentos=0
:reintento_push
git push
if not errorlevel 1 goto desplegar
set /a intentos+=1
if %intentos% geq 5 goto fallo_red
echo   Fallo de red al subir. Reintento %intentos% de 5...
timeout /t 6 >nul
goto reintento_push

:desplegar
echo.
echo === 3/3  Desplegando en Vercel ===
vc deploy web --prod --yes --project clandestino1920
if errorlevel 1 goto fallo

echo.
echo ============================================================
echo   LISTO
echo   Presentacion:  https://clandestino1920.vercel.app
echo   Galeria:       https://clandestino1920.vercel.app/demo.html
echo ============================================================
echo.
pause
exit /b 0

:fallo_red
echo.
echo [ERROR] No se pudo subir a GitHub tras 5 intentos (problema de red/DNS).
echo         Prueba a cambiar de red o espera un momento y vuelve a ejecutar.
pause
exit /b 1

:fallo
echo.
echo [ERROR] Algo ha fallado. Lee el mensaje de arriba.
pause
exit /b 1
