@echo off
REM ---------------------------------------------------------------
REM  Clandestino 1920 - arranca el panel de la demo
REM  Doble clic en este archivo. Se abre solo en el navegador.
REM ---------------------------------------------------------------
cd /d "%~dp0"
REM limpiar variables de Python que puedan venir heredadas de otro programa
set "PYTHONPATH="
set "PYTHONHOME="

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  [ERROR] No encuentro el entorno .venv en esta carpeta.
    echo  Comprueba que estas en C:\Proyectos\Clandestino1920
    echo.
    pause
    exit /b 1
)

echo.
echo  Arrancando el panel de Clandestino 1920...
echo  Tarda unos 40 segundos en cargar los modelos. No cierres esta ventana.
echo  Se abrira solo en:  http://127.0.0.1:5000
echo  Para pararlo: Ctrl+C
echo.

".venv\Scripts\python.exe" app.py

echo.
echo  El panel se ha detenido.
pause
