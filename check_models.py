# check_models.py
from groq import Groq
import os
from pathlib import Path

# Carga .env
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

client = Groq(api_key=os.environ["GROQ_API_KEY"])
models = client.models.list()

print("📋 MODELOS DISPONIBLES EN TU CUENTA GROQ:\n")
for m in models.data:
    print(f"  ✅ {m.id}")
    print(f"      owned_by: {m.owned_by} | context: {m.context_window}")
    print()
