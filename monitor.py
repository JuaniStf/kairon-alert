#!/usr/bin/env python3
"""Monitor de usados de Kairon Music y alertas por Telegram.

No usa APIs no oficiales de Kairon ni de Telegram. Guarda una pequeña base
local (state.json) para saber qué productos ya avisó.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

URL = "https://www.kaironmusic.com.ar/usados/con-stock/"
ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state.json"
ENV_FILE = ROOT / ".env"


def load_env() -> None:
    """Carga KEY=VALUE de .env sin depender de paquetes externos."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    price: str
    url: str


def fetch_products() -> list[Product]:
    request = urllib.request.Request(URL, headers={"User-Agent": "KaironAlert/1.0 (+personal stock monitor)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8", errors="replace")

    # Cada tarjeta Tiendanube contiene el ID, las variantes (con stock) y URL.
    cards = re.findall(r'<div class="js-item-product\b.*?(?=<div class="js-item-product\b|\Z)', page, flags=re.DOTALL)
    products: list[Product] = []
    for card in cards:
        product_id = re.search(r'data-product-id="(\d+)"', card)
        href = re.search(r'<a href="([^"]+)"[^>]*title="([^"]+)"', card)
        variants = re.search(r'data-variants="(\[.*?\])"', card, flags=re.DOTALL)
        if not (product_id and href and variants):
            continue
        try:
            options = json.loads(html.unescape(variants.group(1)))
        except json.JSONDecodeError:
            continue
        available = next((variant for variant in options if variant.get("available") and variant.get("stock", 0) > 0), None)
        if not available:
            continue
        products.append(Product(
            id=product_id.group(1),
            name=html.unescape(href.group(2)).strip(),
            price=available.get("price_short") or available.get("price_long") or "Precio no informado",
            url=html.unescape(href.group(1)),
        ))
    return products


def read_state() -> dict:
    if not STATE_FILE.exists():
        return {"initialized": False, "products": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise RuntimeError("No pude leer state.json. Renombralo o borrálo para crear una base nueva.")


def write_state(products: list[Product]) -> None:
    data = {"initialized": True, "products": [asdict(product) for product in products]}
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_FILE)


def telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID en .env")
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": message, "disable_web_page_preview": "true"}).encode()
    request = urllib.request.Request(endpoint, data=body, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Telegram rechazó el mensaje.")


def format_alert(product: Product) -> str:
    return f"🚨 NUEVO USADO EN KAIRON\n\n{product.name}\nPrecio: {product.price}\n\n{product.url}"


def check(send_initial: bool = False) -> None:
    products = fetch_products()
    if not products:
        logging.warning("Kairon respondió sin productos con stock; no actualizo la base para evitar falsos cambios.")
        return
    state = read_state()
    old_ids = {item["id"] for item in state.get("products", [])}
    if not state.get("initialized"):
        write_state(products)
        logging.info("Base inicial creada con %d productos. No se enviaron alertas.", len(products))
        if send_initial:
            telegram(f"✅ Kairon Alert quedó conectado. Detecté {len(products)} usados con stock y desde ahora te aviso los nuevos.")
        return
    new_products = [product for product in products if product.id not in old_ids]
    for product in new_products:
        telegram(format_alert(product))
        logging.info("Alerta enviada: %s", product.name)
    write_state(products)
    logging.info("Revisión lista: %d disponibles, %d nuevos.", len(products), len(new_products))


def main() -> int:
    load_env()
    interval = max(60, int(os.environ.get("CHECK_EVERY_SECONDS", "300")))
    once = "--once" in sys.argv
    notify_start = "--notify-start" in sys.argv
    try:
        if once:
            check(send_initial=notify_start)
            return 0
        logging.info("Monitor iniciado: revisando cada %d segundos.", interval)
        while True:
            try:
                check(send_initial=notify_start)
                notify_start = False
            except Exception as error:  # sigue funcionando si falla una revisión puntual
                logging.exception("Falló la revisión: %s", error)
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Monitor detenido.")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    raise SystemExit(main())
