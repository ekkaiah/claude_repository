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

PROMPT = """Ets un comercial expert en venda de vehicles de segona mà. La teva feina és identificar el cotxe de la foto i crear un anunci irresistible per vendre'l ràpidament.

Respon OBLIGATÒRIAMENT en català i exactament amb aquest format:

Marca: [marca del cotxe]
Model: [model del cotxe]
Any aproximat: [any o rang d'anys]
Color exterior: [color en català: negre, blanc, vermell, blau, gris, plata, etc.]
Tipus de carrosseria: [Berlina / SUV / Familiar / Esportiu / Monovolum / Pickup / Cabriolet]
Descripció: [Exactament 2 frases en català. Primera frase: per a quin conductor és ideal i quin estil de vida representa. Segona frase: per què és una oportunitat única que no pot deixar escapar. To directe, entusiasta i persuasiu. Sense repetir la marca ni el model.]

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
