"""WF06 — Synchro Stock CJ.

Cron toutes les 4h.
Pour chaque produit Gavio dans WooCommerce avec un meta `_cj_vid`,
interroge CJ pour le stock dispo, met a jour WooCommerce en batch.
"""
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from automation.utils.error_handling import workflow_handler
from automation.workflows import get_cj, get_wc, get_telegram

log = logging.getLogger("automation.wf06")
PARIS = ZoneInfo("Europe/Paris")


def _get_cj_vid(product: dict) -> str:
    """Recupere le meta `_cj_vid` (variant ID CJ) d'un produit WC."""
    for m in product.get("meta_data", []) or []:
        if m.get("key") == "_cj_vid":
            return str(m.get("value") or "")
    return ""


@workflow_handler("wf06_sync_stock_cj")
def run():
    cj = get_cj()
    wc = get_wc()
    tg = get_telegram()

    started = time.time()

    # 1. Recupere tous les produits WC publies
    wc_products = wc.get_products(status="publish")
    log.info("WC : %d produits", len(wc_products))

    # 2. Pour chacun, requete stock CJ
    updates = []
    out_of_stock = 0
    back_in_stock = 0
    details = []
    no_vid = 0

    for prod in wc_products:
        vid = _get_cj_vid(prod)
        if not vid:
            no_vid += 1
            continue

        cur_stock = prod.get("stock_quantity") or 0
        try:
            new_stock = cj.get_product_stock(vid)
        except Exception as e:
            log.warning("get_product_stock(%s) failed: %s", vid, e)
            continue

        if cur_stock != new_stock:
            new_status = "instock" if new_stock > 0 else "outofstock"
            updates.append({
                "id": prod["id"],
                "stock_quantity": new_stock,
                "stock_status": new_status,
                "manage_stock": True,
            })
            if new_stock == 0 and cur_stock > 0:
                out_of_stock += 1
            elif new_stock > 0 and cur_stock == 0:
                back_in_stock += 1
            details.append(
                f"{prod.get('sku', '?')}: {cur_stock} -> {new_stock}"
            )

    # 3. Batch update
    errors = 0
    if updates:
        try:
            wc.batch_update_products(updates, batch_size=10, delay=2.0)
        except Exception as e:
            errors += 1
            log.error("Batch update failed: %s", e)

    duration = int(time.time() - started)
    emoji = "\U0001f504" if updates else "✅"
    now_str = datetime.now(tz=PARIS).strftime("%d/%m/%Y %H:%M")

    details_text = "\n".join(details[:15])
    if len(details) > 15:
        details_text += f"\n... et {len(details) - 15} autres"

    msg = (
        f"{emoji} *Synchro stock CJ — Gavio*\n"
        f"\U0001f4c5 {now_str}\n\n"
        f"\U0001f6d2 Produits WC : {len(wc_products)}\n"
        f"\U0001f517 Avec _cj_vid : {len(wc_products) - no_vid}\n"
        f"\U0001f504 Changements : {len(updates)}\n"
        f"❌ Ruptures : {out_of_stock}\n"
        f"✅ Retour stock : {back_in_stock}\n"
        f"⚠️ Erreurs : {errors}\n\n"
        f"⏱️ Duree : {duration}s"
    )
    if details_text:
        msg += f"\n\n*Details :*\n```\n{details_text}\n```"
    tg.send_message(msg)
    log.info("Stock sync done: %d changes in %ds", len(updates), duration)
    return {"status": "ok", "updates": len(updates), "duration_s": duration}
