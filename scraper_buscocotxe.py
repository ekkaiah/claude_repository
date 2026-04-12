#!/usr/bin/env python3
"""
Scraper de buscocotxe.ad
Extreu tots els detalls dels anuncis de cotxes i els guarda en SQLite.
"""

import sqlite3
import re
import time
import random
import urllib.request
import urllib.error
import http.cookiejar
import gzip
from datetime import datetime

BASE_URL = "https://www.buscocotxe.ad"
DB_FILE = "buscocotxe.db"
DELAY_MIN = 5    # segons mínim entre peticions
DELAY_MAX = 12   # segons màxim
DELAY_EXTRA_PROB = 0.2  # 20% de cops pausa extra llarga

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
]

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


# ─── Base de dades ─────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cotxes (
            id_anunci    INTEGER PRIMARY KEY,
            url          TEXT UNIQUE,
            titol        TEXT,
            preu         TEXT,
            -- Fitxa tècnica
            tipus        TEXT,
            marca        TEXT,
            gamma        TEXT,
            model        TEXT,
            versio       TEXT,
            color_ext    TEXT,
            color_int    TEXT,
            estat        TEXT,
            traccio      TEXT,
            canvi        TEXT,
            combustible  TEXT,
            quilometres  INTEGER,
            places       INTEGER,
            portes       TEXT,
            potencia_cv  INTEGER,
            par_motor_nm INTEGER,
            consum_mig   TEXT,
            data_fabricacio TEXT,
            data_itv     TEXT,
            data_revisio TEXT,
            disponibilitat TEXT,
            matricula    TEXT,
            -- Venedor
            venedor      TEXT,
            telefon      TEXT,
            -- Contingut
            descripcio   TEXT,
            imatges      TEXT,   -- URLs separades per |
            num_imatges  INTEGER,
            -- Meta
            data_scraping TEXT
        )
    """)
    conn.commit()
    return conn


# ─── Xarxa ─────────────────────────────────────────────────────────────────────

def fetch(url, referer=None):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ca,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin" if referer else "none",
        "Referer": referer or BASE_URL + "/ca",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req, timeout=15) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding", "") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} → {url}")
        if e.code == 429:
            print("  Rate limit! Esperant 90s...")
            time.sleep(90)
        return None
    except Exception as e:
        print(f"  Error xarxa: {e}")
        return None


def wait():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    if random.random() < DELAY_EXTRA_PROB:
        t += random.uniform(10, 30)
        print(f"  ⏸  Pausa llarga {t:.0f}s...")
    else:
        print(f"  ⏳ Esperant {t:.1f}s...")
    time.sleep(t)


# ─── Parsing ───────────────────────────────────────────────────────────────────

def clean(text):
    text = re.sub(r'<[^>]+>', '', text)
    replacements = {
        '&euro;': '€', '&amp;': '&', '&ograve;': 'ò', '&egrave;': 'è',
        '&eacute;': 'é', '&agrave;': 'à', '&iacute;': 'í', '&oacute;': 'ó',
        '&uacute;': 'ú', '&ntilde;': 'ñ', '&ccedil;': 'ç', '&#39;': "'",
        '&nbsp;': ' ', '&lt;': '<', '&gt;': '>',
    }
    for ent, char in replacements.items():
        text = text.replace(ent, char)
    return ' '.join(text.split()).strip()


def to_int(text):
    text = re.sub(r'[^\d]', '', text)
    return int(text) if text else None


def parse_listing_page(html):
    urls = re.findall(r'href="(https://www\.buscocotxe\.ad/ca/cotxe/\d+/[^"]+)"', html)
    return list(dict.fromkeys(urls))


def parse_car(html, url):
    # ID de l'anunci
    id_m = re.search(r'/cotxe/(\d+)/', url)
    id_anunci = int(id_m.group(1)) if id_m else None

    # Títol (h1)
    titol_m = re.search(r'<h1[^>]*>.*?>(.*?)</h1>', html, re.S)
    titol = clean(titol_m.group(1)) if titol_m else ""

    # Preu
    preu_m = re.search(r'class="preu[^"]*"[^>]*>\s*([\d\s\.,]+\s*(?:&euro;|€)[^<]*)', html)
    preu = clean(preu_m.group(1)) if preu_m else "Consultar"

    # Fitxa tècnica: tots els parells label/valor de la taula
    fitxa = {}
    rows = re.findall(
        r'<td class="uk-width-1-3">\s*(.*?)\s*</td>\s*<td class="uk-width-3-3 uk-text-bold">\s*(.*?)\s*</td>',
        html, re.S
    )
    for label, value in rows:
        fitxa[clean(label).lower()] = clean(value)

    # Descripció
    desc_m = re.search(r'id="fitxa-item-desc"[^>]*>(.*?)</div>', html, re.S)
    descripcio = clean(desc_m.group(1))[:2000] if desc_m else ""

    # Imatges (URLs úniques)
    imgs = re.findall(
        r'(https://www\.buscocotxe\.ad/uploads/fotos_items/[^\s"\']+\.(?:jpg|jpeg|png))',
        html
    )
    imgs_uniq = list(dict.fromkeys(imgs))

    # Venedor (alt del logo)
    venedor_m = re.search(r'<img src="[^"]+/uploads/users/[^"]*" alt="([^"]+)"', html)
    venedor = venedor_m.group(1) if venedor_m else ""

    # Telèfon
    tel_m = re.search(r'tel:([\d\+\s]{6,15})', html)
    telefon = tel_m.group(1).strip() if tel_m else ""

    # Matricula (ofuscada amb R...)
    mat_m = re.search(r'Matricula[^>]*>[^>]*>\s*([A-Z0-9\.]+)', html)
    matricula = fitxa.get("matricula", mat_m.group(1) if mat_m else "")

    return {
        "id_anunci":       id_anunci,
        "url":             url,
        "titol":           titol,
        "preu":            preu,
        "tipus":           fitxa.get("tipus", ""),
        "marca":           fitxa.get("marca", ""),
        "gamma":           fitxa.get("gamma", ""),
        "model":           fitxa.get("model", ""),
        "versio":          fitxa.get("versió", fitxa.get("versio", "")),
        "color_ext":       fitxa.get("color exterior", ""),
        "color_int":       fitxa.get("color interior", ""),
        "estat":           fitxa.get("estat", ""),
        "traccio":         fitxa.get("tracció", fitxa.get("traccio", "")),
        "canvi":           fitxa.get("canvi", ""),
        "combustible":     fitxa.get("combustible", ""),
        "quilometres":     to_int(fitxa.get("quilòmetres", fitxa.get("quilometres", ""))),
        "places":          to_int(fitxa.get("places", "")),
        "portes":          fitxa.get("portes", ""),
        "potencia_cv":     to_int(fitxa.get("potència (cv)", fitxa.get("potencia (cv)", ""))),
        "par_motor_nm":    to_int(fitxa.get("par motor (nm)", "")),
        "consum_mig":      fitxa.get("consum mig (l. /100km.)", ""),
        "data_fabricacio": fitxa.get("data fabricació", fitxa.get("data fabricacio", "")),
        "data_itv":        fitxa.get("data propera itv", ""),
        "data_revisio":    fitxa.get("data darrera revisió", fitxa.get("data darrera revisio", "")),
        "disponibilitat":  fitxa.get("disponibilitat", ""),
        "matricula":       matricula,
        "venedor":         venedor,
        "telefon":         telefon,
        "descripcio":      descripcio,
        "imatges":         "|".join(imgs_uniq[:20]),
        "num_imatges":     len(imgs_uniq),
        "data_scraping":   datetime.now().isoformat(),
    }


# ─── Persistència ──────────────────────────────────────────────────────────────

def save_car(conn, car):
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR REPLACE INTO cotxes VALUES (
                :id_anunci, :url, :titol, :preu,
                :tipus, :marca, :gamma, :model, :versio,
                :color_ext, :color_int, :estat, :traccio, :canvi, :combustible,
                :quilometres, :places, :portes, :potencia_cv, :par_motor_nm,
                :consum_mig, :data_fabricacio, :data_itv, :data_revisio,
                :disponibilitat, :matricula,
                :venedor, :telefon,
                :descripcio, :imatges, :num_imatges,
                :data_scraping
            )
        """, car)
        conn.commit()
        return True
    except Exception as e:
        print(f"  Error BD: {e}")
        return False


def already_scraped(conn, url):
    c = conn.cursor()
    c.execute("SELECT 1 FROM cotxes WHERE url = ?", (url,))
    return c.fetchone() is not None


# ─── Scraper principal ─────────────────────────────────────────────────────────

def scrape(max_pages=5, max_cars=None):
    conn = init_db()
    total = 0
    errors = 0

    for page in range(1, max_pages + 1):
        list_url = f"{BASE_URL}/ca/darrersanuncis?pn={page}"
        print(f"\n{'='*55}")
        print(f"Pàgina {page}/{max_pages}: {list_url}")
        print(f"{'='*55}")

        html = fetch(list_url)
        if not html:
            print("No s'ha pogut obtenir la pàgina. Parant.")
            break

        car_urls = parse_listing_page(html)
        print(f"Trobats {len(car_urls)} anuncis a la pàgina")

        for i, url in enumerate(car_urls):
            if max_cars and total >= max_cars:
                print(f"\nMàxim de {max_cars} cotxes assolit.")
                conn.close()
                return

            slug = url.split('/')[-1][:45]

            if already_scraped(conn, url):
                print(f"  [{i+1:02}/{len(car_urls)}] ✓ Ja extret: {slug}")
                continue

            print(f"  [{i+1:02}/{len(car_urls)}] → {slug}")
            wait()

            car_html = fetch(url, referer=list_url)
            if not car_html:
                errors += 1
                continue

            car = parse_car(car_html, url)
            if save_car(conn, car):
                total += 1
                print(f"    ✅ {car['marca']} {car['model']} | {car['preu']} | {car['quilometres']}km | {car['num_imatges']} fotos")
            else:
                errors += 1

        if page < max_pages:
            print(f"\nFi de pàgina {page}. Pausa entre pàgines...")
            wait()

    conn.close()
    print(f"\n{'='*55}")
    print(f"Finalitzat. Guardats: {total} | Errors: {errors}")
    print(f"Base de dades: {DB_FILE}")


if __name__ == "__main__":
    print("Scraper buscocotxe.ad — tots els detalls")
    print("Delays: 5-12s + pauses aleatòries extra")
    print()
    scrape(max_pages=2, max_cars=10)
