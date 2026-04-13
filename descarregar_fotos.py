#!/usr/bin/env python3
"""
Descarrega totes les fotos de cotxes de buscocotxe.ad
Organitza per: fotos/MARCA/MODEL/id_anunci_nom.jpg
"""

import sqlite3
import os
import time
import random
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

DB_FILE = "buscocotxe.db"
FOTOS_DIR = "fotos"
DELAY_MIN = 1.5
DELAY_MAX = 4.0
DELAY_EXTRA_PROB = 0.1  # 10% pausa extra

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def sanitize(text):
    """Neteja text per usar com a nom de carpeta"""
    if not text:
        return "DESCONEGUT"
    chars = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
    return chars.strip().upper()[:30]


def wait():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    if random.random() < DELAY_EXTRA_PROB:
        t += random.uniform(5, 15)
    time.sleep(t)


def download_foto(url, dest_path):
    if os.path.exists(dest_path):
        return "skip"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.buscocotxe.ad/ca/darrersanuncis",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req, timeout=15) as r:
            data = r.read()
        if len(data) < 1000:
            return "error"
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(data)
        return "ok"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limit! Esperant 60s...")
            time.sleep(60)
        return "error"
    except Exception:
        return "error"


def descarregar():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id_anunci, marca, model, imatges FROM cotxes WHERE imatges != ''")
    cotxes = c.fetchall()
    conn.close()

    total_urls = sum(len(row[3].split('|')) for row in cotxes if row[3])
    print(f"Cotxes amb fotos: {len(cotxes)}")
    print(f"Total URLs: {total_urls}")
    print(f"Destí: {FOTOS_DIR}/")
    print()

    ok = skip = errors = 0
    foto_num = 0

    for id_anunci, marca, model, imatges_str in cotxes:
        if not imatges_str:
            continue

        marca_dir = sanitize(marca)
        model_dir = sanitize(model)
        carpeta = os.path.join(FOTOS_DIR, marca_dir, model_dir)

        urls = [u.strip() for u in imatges_str.split('|') if u.strip()]

        for i, url in enumerate(urls):
            foto_num += 1
            ext = url.split('.')[-1].lower().split('?')[0]
            nom = f"{id_anunci}_{i+1:02d}.{ext}"
            dest = os.path.join(carpeta, nom)

            resultat = download_foto(url, dest)

            if resultat == "ok":
                ok += 1
                print(f"  [{foto_num}/{total_urls}] ✅ {marca_dir}/{model_dir}/{nom}")
                wait()
            elif resultat == "skip":
                skip += 1
                if skip % 100 == 0:
                    print(f"  [{foto_num}/{total_urls}] ⏭  Ja existeixen {skip} fotos...")
            else:
                errors += 1
                print(f"  [{foto_num}/{total_urls}] ❌ Error: {url[-40:]}")

        # Resum cada 50 cotxes
        if foto_num % 500 == 0:
            print(f"\n--- Progrés: {foto_num}/{total_urls} | OK:{ok} Skip:{skip} Errors:{errors} ---\n")

    print(f"\nFinalitzat!")
    print(f"Descarregades: {ok} | Ja existien: {skip} | Errors: {errors}")
    print(f"Carpeta: {os.path.abspath(FOTOS_DIR)}")

    # Espai ocupat
    total_size = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, dn, filenames in os.walk(FOTOS_DIR)
        for f in filenames
    )
    print(f"Espai ocupat: {total_size / 1024**3:.2f} GB")


if __name__ == "__main__":
    print("Descarregador de fotos — buscocotxe.ad")
    print("Delays: 1.5-4s entre fotos")
    print()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    descarregar()
