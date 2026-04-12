#!/usr/bin/env python3
"""
Identificació de cotxes amb LLaVA (Ollama local)
Ús: python3 identificar_cotxe.py foto.jpg
"""

import sys
import json
import base64
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llava:7b"

PROMPT = """Ets un expert en vehicles. Analitza aquesta fotografia i respon OBLIGATÒRIAMENT en català (no en anglès, sempre en català).

Respon exactament amb aquest format:

Marca: [marca del cotxe]
Model: [model del cotxe]
Any aproximat: [any o rang d'anys]
Color exterior: [color en català: negre, blanc, vermell, blau, gris, plata, etc.]
Tipus de carrosseria: [Berlina / SUV / Familiar / Esportiu / Monovolum / Pickup / Cabriolet]
Descripció: [2-3 frases en català descrivint el cotxe de forma atractiva per a un comprador potencial]

Tots els camps han d'estar en català. Si no pots identificar algun camp, escriu "No determinat"."""


def identificar(ruta_foto):
    with open(ruta_foto, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    data = json.dumps({
        "model": MODEL,
        "prompt": PROMPT,
        "images": [img_b64],
        "stream": False
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    print(f"Analitzant {ruta_foto}...\n")
    with urllib.request.urlopen(req, timeout=120) as r:
        result = json.loads(r.read())
        print(result["response"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ús: python3 identificar_cotxe.py foto.jpg")
        sys.exit(1)
    identificar(sys.argv[1])
